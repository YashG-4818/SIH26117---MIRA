"""
core/llm.py — the only place that talks to Ollama.

Three things here matter more than the rest:

1. VRAM discipline. On a 8-12 GB laptop shared by four people you cannot hold a
   chat model, a vision model and an embedding model at once. use_model()
   unloads everything else before loading what you asked for. This is the single
   most common cause of "it worked yesterday" failures in local-LLM demos.

2. Tool calling that degrades instead of breaking. Ollama's native tools API is
   tried first. If the model ignores it (open models are inconsistent), we fall
   back to asking for a JSON block and parsing it. The agent loop above does not
   need to know which path was used.

3. Everything is loopback. requests goes to 127.0.0.1 only, and core.netguard
   enforces that at the socket layer.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Iterable

import requests

import config

_SESSION = requests.Session()
_LOADED: set[str] = set()          # what we believe is resident in VRAM
_LAST_ERROR: str | None = None


class LLMError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Low-level HTTP
# ---------------------------------------------------------------------------
def _url(path: str) -> str:
    return config.OLLAMA_HOST.rstrip("/") + path


def _post(path: str, body: dict, timeout: int | None = None,
          stream: bool = False) -> Any:
    global _LAST_ERROR
    try:
        r = _SESSION.post(_url(path), json=body,
                          timeout=timeout or config.OLLAMA_TIMEOUT,
                          stream=stream)
    except requests.exceptions.ConnectionError as exc:
        _LAST_ERROR = str(exc)
        raise LLMError(
            "Cannot reach Ollama at " + config.OLLAMA_HOST + ".\n"
            "Fix: open a terminal and run  ollama serve\n"
            "Then check it is up by visiting " + config.OLLAMA_HOST +
            " in a browser - it should say 'Ollama is running'."
        ) from exc
    except requests.exceptions.ReadTimeout as exc:
        _LAST_ERROR = str(exc)
        raise LLMError(
            f"Ollama did not reply within {timeout or config.OLLAMA_TIMEOUT}s. "
            f"The first request after starting up loads the model into memory "
            f"and can be slow. Try again, or use a smaller model "
            f"(set SIH_CHAT_MODEL=qwen2.5:3b-instruct)."
        ) from exc
    if r.status_code == 404:
        raise LLMError(
            f"Ollama replied 404 for {path}. The model named in config.py is "
            f"probably not pulled yet. Run:  ollama pull {body.get('model','')}"
        )
    if r.status_code >= 400:
        raise LLMError(f"Ollama error {r.status_code}: {r.text[:500]}")
    return r if stream else r.json()


def _get(path: str, timeout: int = 10) -> dict:
    try:
        r = _SESSION.get(_url(path), timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        raise LLMError(f"Ollama GET {path} failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Health and model inventory
# ---------------------------------------------------------------------------
def health() -> dict:
    """Everything the UI and the setup checker need, in one call."""
    out: dict[str, Any] = {"host": config.OLLAMA_HOST, "reachable": False,
                          "models": [], "error": None}
    try:
        tags = _get("/api/tags")
        out["reachable"] = True
        out["models"] = sorted(m["name"] for m in tags.get("models", []))
        out["model_details"] = [
            {"name": m.get("name"),
             "size_gb": round(m.get("size", 0) / 1e9, 2),
             "family": (m.get("details") or {}).get("family"),
             "params": (m.get("details") or {}).get("parameter_size"),
             "quant": (m.get("details") or {}).get("quantization_level")}
            for m in tags.get("models", [])
        ]
    except LLMError as exc:
        out["error"] = str(exc)
        return out
    try:
        out["version"] = _get("/api/version").get("version")
    except LLMError:
        out["version"] = "unknown"
    try:
        ps = _get("/api/ps")
        out["resident"] = [
            {"name": m.get("name"),
             "vram_gb": round(m.get("size_vram", 0) / 1e9, 2),
             "until": m.get("expires_at")}
            for m in ps.get("models", [])
        ]
        out["vram_in_use_gb"] = round(
            sum(m.get("size_vram", 0) for m in ps.get("models", [])) / 1e9, 2)
    except LLMError:
        out["resident"] = []
        out["vram_in_use_gb"] = 0.0
    return out


def available_models() -> list[str]:
    try:
        return health().get("models", [])
    except Exception:  # noqa: BLE001
        return []


def resolve_model(preferred: str, fallbacks: Iterable[str]) -> str | None:
    """Return the first of preferred/fallbacks that is actually pulled.

    Matching is prefix-tolerant so 'qwen2.5:7b-instruct' also matches a locally
    tagged 'qwen2.5:7b-instruct-q4_K_M'.
    """
    have = available_models()
    if not have:
        return None
    for want in [preferred, *fallbacks]:
        for h in have:
            if h == want or h.startswith(want) or h.split(":")[0] == want:
                return h
    return None


def chat_model() -> str:
    m = resolve_model(config.CHAT_MODEL, config.CHAT_MODEL_FALLBACKS)
    if not m:
        raise LLMError(
            f"None of the chat models are pulled. Run:\n"
            f"    ollama pull {config.CHAT_MODEL}\n"
            f"Models currently available: {available_models() or 'none'}"
        )
    return m


def vision_model() -> str | None:
    return resolve_model(config.VISION_MODEL, config.VISION_MODEL_FALLBACKS)


def embed_model() -> str | None:
    return resolve_model(config.EMBED_MODEL, [])


def pull_model(name: str, progress=None) -> bool:
    """Pull a model, reporting progress. Needs the internet, so this is a setup
    step and is never called during a demo."""
    r = _post("/api/pull", {"model": name, "stream": True},
              timeout=3600, stream=True)
    for line in r.iter_lines():
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if progress:
            done, total = msg.get("completed", 0), msg.get("total", 0)
            pct = (done / total * 100) if total else 0
            progress(msg.get("status", ""), pct)
        if msg.get("error"):
            raise LLMError(f"Pull failed: {msg['error']}")
    return True


# ---------------------------------------------------------------------------
# VRAM discipline
# ---------------------------------------------------------------------------
def unload(model: str) -> None:
    """Ask Ollama to drop a model from memory now."""
    try:
        _post("/api/generate",
              {"model": model, "prompt": "", "keep_alive":
               config.KEEP_ALIVE_RELEASE}, timeout=30)
    except LLMError:
        pass
    _LOADED.discard(model)


def unload_all() -> list[str]:
    """Free all VRAM. Call this before the vision model, and after it."""
    freed = []
    try:
        for m in health().get("resident", []):
            name = m.get("name")
            if name:
                unload(name)
                freed.append(name)
    except Exception:  # noqa: BLE001
        pass
    _LOADED.clear()
    return freed


def use_model(model: str) -> None:
    """Make `model` the only thing resident, if sequential loading is on."""
    if not config.SEQUENTIAL_MODEL_LOADING:
        return
    try:
        resident = [m.get("name") for m in health().get("resident", [])]
    except Exception:  # noqa: BLE001
        return
    for other in resident:
        if other and other != model:
            unload(other)
    _LOADED.add(model)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
def _options(**over) -> dict:
    opts = {
        "temperature": config.TEMPERATURE,
        "num_ctx": config.NUM_CTX,
        "num_predict": config.NUM_PREDICT,
    }
    opts.update({k: v for k, v in over.items() if v is not None})
    return opts


def chat(messages: list[dict], *, model: str | None = None,
         tools: list[dict] | None = None, temperature: float | None = None,
         num_predict: int | None = None, manage_vram: bool = True) -> dict:
    """One non-streaming chat turn.

    Returns {"content": str, "tool_calls": [...], "model": str,
             "elapsed_s": float, "eval_tokens": int, "tokens_per_s": float}
    """
    model = model or chat_model()
    if manage_vram:
        use_model(model)
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": config.KEEP_ALIVE,
        "options": _options(temperature=temperature, num_predict=num_predict),
    }
    if tools:
        body["tools"] = tools
    t0 = time.time()
    data = _post("/api/chat", body)
    elapsed = time.time() - t0
    msg = data.get("message", {}) or {}
    eval_count = data.get("eval_count", 0) or 0
    eval_dur = data.get("eval_duration", 0) or 0
    return {
        "content": (msg.get("content") or "").strip(),
        "tool_calls": msg.get("tool_calls") or [],
        "raw_message": msg,
        "model": model,
        "elapsed_s": round(elapsed, 2),
        "eval_tokens": eval_count,
        "prompt_tokens": data.get("prompt_eval_count", 0) or 0,
        "tokens_per_s": round(eval_count / (eval_dur / 1e9), 1)
        if eval_dur else 0.0,
        "done_reason": data.get("done_reason"),
    }


def chat_stream(messages: list[dict], *, model: str | None = None,
                temperature: float | None = None, manage_vram: bool = True):
    """Yield content pieces as they arrive. Used for the typing effect in chat."""
    model = model or chat_model()
    if manage_vram:
        use_model(model)
    body = {
        "model": model, "messages": messages, "stream": True,
        "keep_alive": config.KEEP_ALIVE,
        "options": _options(temperature=temperature),
    }
    r = _post("/api/chat", body, stream=True)
    for line in r.iter_lines():
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        piece = (msg.get("message") or {}).get("content")
        if piece:
            yield piece
        if msg.get("done"):
            break


# ---------------------------------------------------------------------------
# Tool calling, with a fallback for models that ignore the tools API
# ---------------------------------------------------------------------------
_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)
_BARE_OBJ = re.compile(r"(\{[^{}]*\"(?:tool|name|tool_name)\"\s*:.*?\})", re.S)


def _parse_text_tool_call(text: str) -> list[dict]:
    """Recover a tool call from prose. Accepts several shapes models emit."""
    if not text:
        return []
    candidates: list[str] = [m.group(1) for m in _JSON_BLOCK.finditer(text)]
    candidates += [m.group(1) for m in _BARE_OBJ.finditer(text)]
    out = []
    for c in candidates:
        try:
            obj = json.loads(c)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        name = obj.get("tool") or obj.get("name") or obj.get("tool_name")
        args = (obj.get("arguments") or obj.get("args")
                or obj.get("parameters") or {})
        if name and isinstance(args, dict):
            out.append({"function": {"name": str(name), "arguments": args}})
    return out


def normalise_tool_calls(reply: dict) -> list[dict]:
    """Return [{'name':..., 'arguments': {...}}] regardless of how it arrived."""
    calls = []
    for tc in reply.get("tool_calls") or []:
        fn = tc.get("function") or {}
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"_raw": args}
        calls.append({"name": fn.get("name"), "arguments": args or {},
                      "via": "native"})
    if not calls:
        for tc in _parse_text_tool_call(reply.get("content", "")):
            fn = tc["function"]
            calls.append({"name": fn["name"], "arguments": fn["arguments"],
                          "via": "text-fallback"})
    return [c for c in calls if c.get("name")]


def supports_native_tools(model: str | None = None) -> dict:
    """Day-1/Day-2 smoke test: does this model really do tool calling?

    Returns a verdict you can show in the UI, so nobody has to guess.
    """
    model = model or chat_model()
    tools = [{
        "type": "function",
        "function": {
            "name": "get_equipment_status",
            "description": "Get the live running status of a tagged item of "
                           "plant equipment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string",
                            "description": "Equipment tag, e.g. P-2104B"},
                },
                "required": ["tag"],
            },
        },
    }]
    msgs = [
        {"role": "system", "content": "You are a plant assistant. When a tool "
                                      "can answer the question, call it."},
        {"role": "user", "content": "Is pump P-2104B running right now?"},
    ]
    try:
        reply = chat(msgs, model=model, tools=tools)
    except LLMError as exc:
        return {"model": model, "native": False, "fallback": False,
                "ok": False, "detail": str(exc)}
    calls = normalise_tool_calls(reply)
    native = any(c["via"] == "native" for c in calls)
    fallback = bool(calls) and not native
    got_tag = any(str(c["arguments"].get("tag", "")).upper().replace(" ", "")
                  == "P-2104B" for c in calls)
    return {
        "model": model,
        "native": native,
        "fallback": fallback,
        "ok": bool(calls),
        "correct_arguments": got_tag,
        "calls": calls,
        "tokens_per_s": reply["tokens_per_s"],
        "elapsed_s": reply["elapsed_s"],
        "detail": ("Native tool calling works." if native else
                   "No native tool call; the text fallback recovered one."
                   if fallback else
                   "Model did not call the tool. Try a different model."),
        "raw_content": reply["content"][:400],
    }


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
def embed(texts: list[str], *, model: str | None = None,
          batch: int = 16) -> list[list[float]]:
    """Embed a list of strings. Runs on whatever device Ollama chooses; the
    model is small enough for CPU, which keeps VRAM free for the chat model."""
    model = model or embed_model()
    if not model:
        raise LLMError(
            f"Embedding model not found. Run:  ollama pull {config.EMBED_MODEL}"
        )
    out: list[list[float]] = []
    for i in range(0, len(texts), batch):
        chunk = [t if t.strip() else " " for t in texts[i:i + batch]]
        data = _post("/api/embed", {"model": model, "input": chunk},
                     timeout=config.OLLAMA_TIMEOUT)
        vecs = data.get("embeddings")
        if vecs is None and "embedding" in data:
            vecs = [data["embedding"]]
        if not vecs or len(vecs) != len(chunk):
            raise LLMError(
                f"Embedding call returned {0 if not vecs else len(vecs)} "
                f"vectors for {len(chunk)} inputs."
            )
        out.extend(vecs)
    return out


def embed_one(text: str, *, model: str | None = None) -> list[float]:
    return embed([text], model=model)[0]


# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------
def describe_image(image_path: str | Path, prompt: str | None = None,
                   *, model: str | None = None,
                   free_vram_after: bool = True) -> dict:
    """Send one image to a vision model.

    Loads the vision model alone, then unloads it, so the chat model can come
    back into VRAM afterwards. Slower, but it does not OOM mid-demo.
    """
    import base64

    model = model or vision_model()
    if not model:
        return {"ok": False,
                "text": "",
                "error": f"No vision model available. Run:  ollama pull "
                         f"{config.VISION_MODEL}"}
    p = Path(image_path)
    if not p.exists():
        return {"ok": False, "text": "", "error": f"No such image: {p}"}

    prompt = prompt or (
        "This is an engineering document or drawing from an oil refinery. "
        "Transcribe every piece of text, equipment tag, number and label you "
        "can see, exactly as written. Then describe in two sentences what the "
        "drawing shows. Do not guess at anything you cannot read - write "
        "[unclear] instead."
    )
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    unload_all()
    try:
        data = _post("/api/chat", {
            "model": model,
            "messages": [{"role": "user", "content": prompt, "images": [b64]}],
            "stream": False,
            "keep_alive": config.KEEP_ALIVE,
            "options": _options(temperature=0.05, num_predict=900),
        })
        text = ((data.get("message") or {}).get("content") or "").strip()
        return {"ok": True, "text": text, "model": model,
                "error": None}
    except LLMError as exc:
        return {"ok": False, "text": "", "model": model, "error": str(exc)}
    finally:
        if free_vram_after:
            unload(model)


# ---------------------------------------------------------------------------
# Benchmark (Person A's deliverable)
# ---------------------------------------------------------------------------
def benchmark(model: str | None = None, runs: int = 3) -> dict:
    """Measure cold and warm latency plus throughput, for the pitch deck."""
    model = model or chat_model()
    prompt = ("In exactly three sentences, explain why a refinery would run a "
              "language model on its own hardware instead of in the cloud.")
    msgs = [{"role": "user", "content": prompt}]
    unload_all()
    samples = []
    for i in range(runs):
        t0 = time.time()
        r = chat(msgs, model=model, manage_vram=(i == 0))
        samples.append({
            "run": i + 1,
            "kind": "cold" if i == 0 else "warm",
            "wall_s": round(time.time() - t0, 2),
            "tokens": r["eval_tokens"],
            "tokens_per_s": r["tokens_per_s"],
        })
    warm = [s for s in samples if s["kind"] == "warm"]
    h = health()
    return {
        "model": model,
        "samples": samples,
        "cold_start_s": samples[0]["wall_s"],
        "warm_mean_s": round(sum(s["wall_s"] for s in warm) / len(warm), 2)
        if warm else None,
        "warm_mean_tps": round(sum(s["tokens_per_s"] for s in warm) / len(warm), 1)
        if warm else None,
        "vram_gb": h.get("vram_in_use_gb"),
        "resident": h.get("resident"),
    }
