"""
agent.py — the reasoning loop: LLM + tools + a human approval gate + an audit
trail. This sits one level above core/ and is what app.py talks to.

The loop itself is deliberately small. Each turn:

  1. Send the conversation + tool schemas to llm.chat().
  2. llm.normalise_tool_calls() tells us if the model wants to call a tool,
     whether it used Ollama's native tools API or we had to recover a JSON
     block from plain text - the agent does not need to care which.
  3. If no tool call: that is the final answer, we stop.
  4. If there IS a tool call: if the tool is marked requires_approval (writing
     a file, running code), we STOP and hand control back to app.py, which
     shows the person an Approve/Reject button. Nothing runs until they click.
     This pause is not a UI nicety - it is the second demo differentiator
     alongside the air-gap guard, and it is real: no code executes and no file
     is written between "the model asked" and "a human said yes".
  5. Otherwise (a read-only search tool) we just run it and loop again.

MAX_AGENT_STEPS (config.py) bounds how many turns this can take, so a model
that gets stuck calling tools in a loop cannot spin forever - it stops and
says so instead.

Because Streamlit reruns the whole script on every interaction, an Agent
instance is meant to be created once per session and kept in
st.session_state. Calling ask() / approve() / reject() mutates it in place
and returns a list of "events" describing what just happened, which app.py
renders. Nothing here imports streamlit - this file has no idea what the UI
looks like, on purpose.
"""

from __future__ import annotations

import json
import textwrap
from typing import Any

import config
from core import audit, kb, llm, outputs, sandbox

# ---------------------------------------------------------------------------
# Tool schemas (the JSON-schema shape Ollama's /api/chat tools field expects)
# ---------------------------------------------------------------------------
_SCHEMA_SEARCH = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": (
            "Search the MRPL document corpus (SOPs, maintenance logs, "
            "inspection checklists, incident reports) for passages relevant "
            "to a question. Always use this before answering a factual "
            "question about plant documents, equipment or procedures."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for - plain language, an "
                                   "equipment tag, or a document id.",
                },
                "k": {
                    "type": "integer",
                    "description": "How many passages to return. Omit for "
                                   "the default; raise it for a broad "
                                   "question spanning several documents.",
                },
                "doc_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Restrict the search to these document "
                                   "ids, if the person named one.",
                },
            },
            "required": ["query"],
        },
    },
}

_SCHEMA_DOSSIER = {
    "type": "function",
    "function": {
        "name": "get_equipment_dossier",
        "description": (
            "Get everything the corpus says about one tagged item of "
            "equipment (e.g. P-2104B, PSV-2141), pulled from every document "
            "that mentions it. Use this instead of search_knowledge_base "
            "when the question is clearly about a specific tag."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "The equipment tag."},
            },
            "required": ["tag"],
        },
    },
}

_SCHEMA_LIST_DOCS = {
    "type": "function",
    "function": {
        "name": "list_documents",
        "description": "List every document currently in the knowledge "
                       "base, with its id, title and type. Use this when the "
                       "person asks what documents exist or seems unsure "
                       "what to ask about.",
        "parameters": {"type": "object", "properties": {}},
    },
}

_SCHEMA_LIST_TAGS = {
    "type": "function",
    "function": {
        "name": "list_equipment_tags",
        "description": "List equipment tags known to the corpus and how "
                       "often each is mentioned. Use this when the person "
                       "is not sure of the exact tag they mean.",
        "parameters": {"type": "object", "properties": {}},
    },
}

_SCHEMA_SANDBOX = {
    "type": "function",
    "function": {
        "name": "run_python_calculation",
        "description": (
            "Run a short, sandboxed Python calculation - arithmetic, "
            "statistics, unit conversion, trend fitting. Use this instead of "
            "computing the answer yourself: a number you cannot audit is a "
            "number a plant engineer should not trust, and language models "
            "get arithmetic wrong more often than they let on. Assign your "
            "final answer to a variable named result. Pauses for a human's "
            "approval before it runs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python source. Assign the answer to "
                                   "`result`. Only a safe subset of the "
                                   "standard library plus numpy, pandas and "
                                   "matplotlib is available - no files, "
                                   "network or subprocesses.",
                },
                "data": {
                    "type": "object",
                    "description": "Optional JSON-serialisable data made "
                                   "available to the code as a variable "
                                   "named DATA.",
                },
            },
            "required": ["code"],
        },
    },
}

_SCHEMA_DOCUMENT = {
    "type": "function",
    "function": {
        "name": "generate_document",
        "description": (
            "Generate a Word, PDF or PowerPoint file from an answer, stamped "
            "with a provenance block (question, model, sources cited, audit "
            "chain hash). Only call this when the person clearly asks for a "
            "document, report, file, or something to save or share - not "
            "for an ordinary chat answer. Pauses for a human's approval "
            "before it writes to disk."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["docx", "pdf", "pptx"]},
                "title": {"type": "string"},
                "content_markdown": {
                    "type": "string",
                    "description": "The document body in simple markdown: "
                                   "'#'/'##' headings, '**bold**', '-' "
                                   "bullets. Keep citations in square "
                                   "brackets exactly as given to you.",
                },
                "question": {
                    "type": "string",
                    "description": "Optional. Defaults to the question the "
                                   "person just asked.",
                },
            },
            "required": ["format", "title", "content_markdown"],
        },
    },
}

_SCHEMA_XLSX = {
    "type": "function",
    "function": {
        "name": "generate_spreadsheet",
        "description": (
            "Generate an Excel file from a table of data, with an optional "
            "line chart and a Provenance sheet. Pauses for a human's "
            "approval before it writes to disk."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "table": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "A list of row objects (column name -> "
                                   "value), or a list of lists with the "
                                   "header as the first row.",
                },
                "chart": {
                    "type": "object",
                    "description": "Optional: {\"x\": \"Column name\", "
                                   "\"y\": [\"Col A\", \"Col B\"], "
                                   "\"title\": \"...\"}",
                },
                "notes": {"type": "string"},
            },
            "required": ["title", "table"],
        },
    },
}

_SCHEMA_CHART = {
    "type": "function",
    "function": {
        "name": "generate_chart",
        "description": (
            "Generate a publication-quality PNG chart (line or bar), "
            "optionally with horizontal limit lines (e.g. alert / trip "
            "thresholds) - this is what makes a vibration or throughput "
            "chart mean something rather than just plotting numbers. "
            "Pauses for a human's approval before it writes to disk."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "x": {
                    "type": "array", "items": {},
                    "description": "Category or x-axis values.",
                },
                "series": {
                    "type": "object",
                    "description": "Map of series name -> list of numbers, "
                                   "the same length as x.",
                },
                "y_label": {"type": "string"},
                "x_label": {"type": "string"},
                "kind": {"type": "string", "enum": ["line", "bar"]},
                "hlines": {
                    "type": "array", "items": {"type": "object"},
                    "description": "Optional limit lines, e.g. "
                                   "[{\"y\": 7.1, \"label\": \"Alert\", "
                                   "\"color\": \"#B3261E\"}]",
                },
            },
            "required": ["title", "x", "series"],
        },
    },
}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
def _system_prompt() -> str:
    return textwrap.dedent(f"""
        You are the {config.APP_NAME}, an on-premise assistant for
        {config.ORG}. You run entirely on this machine - nothing you say or
        do reaches the internet.

        Ground every factual claim in the knowledge base. Before answering a
        question about plant documents, equipment, SOPs, incidents or
        inspections, call search_knowledge_base or get_equipment_dossier.
        Never invent a document number, work order, tag or figure - if you
        cannot find it, say plainly that you could not find it.

        When you state a fact from a source, cite it in square brackets
        exactly as it was given to you by the tool, e.g. [SOP-CDU2-014 p.3].
        Only cite sources a tool actually returned to you in this
        conversation.

        For arithmetic, statistics, unit conversions or trend calculations,
        call run_python_calculation rather than computing it yourself.

        Only call generate_document, generate_spreadsheet or generate_chart
        when the person clearly asks for a file, a report, a chart, or
        something to save or share. A plain chat answer is preferred
        otherwise.

        Tools that run code or write a file pause for a human's approval
        before they execute. That is expected behaviour, not a failure -
        wait for the tool result before continuing.
    """).strip()


def _hits_payload(hits: list[dict]) -> dict:
    """Shape kb.search()/kb.search_by_tag() results for the model, and pull
    out the citation strings so the agent can stamp them onto any document it
    later generates."""
    citations = sorted({h.get("citation") for h in hits if h.get("citation")})
    return {
        "results": [
            {
                "citation": h.get("citation"),
                "doc_id": h.get("doc_id"),
                "title": h.get("title"),
                "text": h.get("text"),
                "score": h.get("score"),
            }
            for h in hits
        ],
        "count": len(hits),
        "_citations": citations,   # stripped out before the model sees it
    }


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class Agent:
    """One conversation. Create one per Streamlit session and keep it in
    st.session_state - do not build a new one per message, or history and
    the approval gate both break."""

    def __init__(self) -> None:
        self.messages: list[dict] = [
            {"role": "system", "content": _system_prompt()}
        ]
        self.last_citations: list[str] = []
        self.last_question: str = ""
        self.pending: dict | None = None   # a tool call awaiting a human click
        self.step_count = 0

        # Bound per-instance so each tool can reach self.last_citations /
        # self.last_question without any module-level global state.
        self.tools: dict[str, dict] = {
            "search_knowledge_base": {
                "schema": _SCHEMA_SEARCH, "requires_approval": False,
                "fn": self._tool_search_kb,
            },
            "get_equipment_dossier": {
                "schema": _SCHEMA_DOSSIER, "requires_approval": False,
                "fn": self._tool_dossier,
            },
            "list_documents": {
                "schema": _SCHEMA_LIST_DOCS, "requires_approval": False,
                "fn": self._tool_list_documents,
            },
            "list_equipment_tags": {
                "schema": _SCHEMA_LIST_TAGS, "requires_approval": False,
                "fn": self._tool_list_tags,
            },
            "run_python_calculation": {
                "schema": _SCHEMA_SANDBOX, "requires_approval": True,
                "fn": self._tool_sandbox,
            },
            "generate_document": {
                "schema": _SCHEMA_DOCUMENT, "requires_approval": True,
                "fn": self._tool_document,
            },
            "generate_spreadsheet": {
                "schema": _SCHEMA_XLSX, "requires_approval": True,
                "fn": self._tool_xlsx,
            },
            "generate_chart": {
                "schema": _SCHEMA_CHART, "requires_approval": True,
                "fn": self._tool_chart,
            },
        }

    def tool_schemas(self) -> list[dict]:
        return [t["schema"] for t in self.tools.values()]

    # -- conversation entry points -------------------------------------
    def ask(self, question: str) -> list[dict]:
        """Start answering a new question. Returns a list of events; see
        _advance() for the shapes."""
        self.last_question = question
        self.messages.append({"role": "user", "content": question})
        self.step_count = 0
        return self._advance()

    def approve(self) -> list[dict]:
        """The human clicked Approve on the pending tool call."""
        if not self.pending:
            return []
        name, tool, arguments = (self.pending["name"], self.pending["tool"],
                                 self.pending["arguments"])
        self.pending = None
        audit.log("agent.tool_approved",
                  {"tool": name, "arguments": arguments}, actor="human")
        result = self._invoke(name, tool, arguments)
        events = [{"type": "tool_result", "name": name,
                  "arguments": arguments, "result": result,
                  "was_approved": True}]
        events.extend(self._advance())
        return events

    def reject(self, reason: str = "") -> list[dict]:
        """The human clicked Reject on the pending tool call. Nothing runs;
        the model is told it was declined and gets a chance to respond."""
        if not self.pending:
            return []
        name, arguments = self.pending["name"], self.pending["arguments"]
        self.pending = None
        audit.log("agent.tool_declined",
                  {"tool": name, "arguments": arguments, "reason": reason},
                  actor="human")
        result = {"declined": True,
                  "reason": reason or "Declined by the operator."}
        self.messages.append({"role": "tool", "content": json.dumps(result)})
        events = [{"type": "tool_declined", "name": name, "result": result}]
        events.extend(self._advance())
        return events

    def reset(self) -> None:
        self.__init__()

    # -- the loop --------------------------------------------------------
    def _advance(self) -> list[dict]:
        """Run turns until we get a final answer, hit an approval gate, or
        exhaust config.MAX_AGENT_STEPS. Returns the events from this call
        only (not the whole conversation)."""
        events: list[dict] = []
        while self.step_count < config.MAX_AGENT_STEPS:
            self.step_count += 1
            try:
                reply = llm.chat(self.messages, tools=self.tool_schemas())
            except llm.LLMError as exc:
                events.append({"type": "error", "text": str(exc)})
                return events

            calls = llm.normalise_tool_calls(reply)
            # Record exactly what the model produced, tool_calls and all, so
            # the next turn's history is faithful to what actually happened -
            # this matters whether the call came via Ollama's native tools
            # API or was recovered from a JSON block in plain text.
            self.messages.append(reply.get("raw_message")
                                 or {"role": "assistant",
                                     "content": reply["content"]})

            if not calls:
                events.append({
                    "type": "answer", "text": reply["content"],
                    "model": reply["model"], "elapsed_s": reply["elapsed_s"],
                })
                return events

            call = calls[0]   # one tool per turn keeps the approval gate simple
            name, arguments = call["name"], call["arguments"]
            tool = self.tools.get(name)

            if tool is None:
                result = {"error": f"Unknown tool '{name}'. Available: "
                                   f"{', '.join(self.tools)}"}
                self.messages.append(
                    {"role": "tool", "content": json.dumps(result)})
                events.append({"type": "tool_error", "name": name,
                              "result": result})
                continue

            if tool["requires_approval"] and config.REQUIRE_APPROVAL:
                self.pending = {"name": name, "tool": tool,
                                "arguments": arguments}
                audit.log("agent.approval_requested",
                          {"tool": name, "arguments": arguments},
                          actor="agent")
                events.append({"type": "approval_required", "name": name,
                              "arguments": arguments})
                return events

            result = self._invoke(name, tool, arguments)
            events.append({"type": "tool_result", "name": name,
                          "arguments": arguments, "result": result})

        events.append({
            "type": "error",
            "text": f"Stopped after {config.MAX_AGENT_STEPS} steps without a "
                    f"final answer. Try a narrower question.",
        })
        return events

    def _invoke(self, name: str, tool: dict, arguments: dict) -> dict:
        """Actually call a tool function, capture citations, append the tool
        result to history, and audit-log it. Never raises - a tool that
        blows up becomes an {"error": ...} the model can react to."""
        try:
            result = tool["fn"](arguments or {})
        except Exception as exc:  # noqa: BLE001
            result = {"error": f"{type(exc).__name__}: {exc}"}

        citations = (result.pop("_citations", None)
                    if isinstance(result, dict) else None)
        if citations:
            for c in citations:
                if c and c not in self.last_citations:
                    self.last_citations.append(c)

        payload = json.dumps(result, default=str)
        if len(payload) > config.MAX_TOOL_RESULT_CHARS:
            payload = payload[:config.MAX_TOOL_RESULT_CHARS] + "...[truncated]"
        self.messages.append({"role": "tool", "content": payload})

        audit.log("agent.tool_used",
                  {"tool": name, "arguments": arguments,
                   "ok": isinstance(result, dict) and "error" not in result},
                  actor="agent")
        return result

    # -- tool implementations ---------------------------------------------
    def _tool_search_kb(self, args: dict) -> dict:
        query = str(args.get("query", "")).strip()
        if not query:
            return {"error": "query is required"}
        k = args.get("k")
        try:
            k = int(k) if k not in (None, "") else None
        except (TypeError, ValueError):
            k = None
        doc_filter = args.get("doc_filter")
        if isinstance(doc_filter, str):
            doc_filter = [doc_filter]
        hits = kb.search(query, k=k, doc_filter=doc_filter)
        return _hits_payload(hits)

    def _tool_dossier(self, args: dict) -> dict:
        tag = str(args.get("tag", "")).strip()
        if not tag:
            return {"error": "tag is required"}
        hits = kb.search_by_tag(tag)
        out = _hits_payload(hits)
        out["tag"] = tag
        return out

    def _tool_list_documents(self, _args: dict) -> dict:
        return {"documents": kb.documents()}

    def _tool_list_tags(self, _args: dict) -> dict:
        tags = kb.all_tags()
        return {"tags": tags[:80], "total": len(tags)}

    def _tool_sandbox(self, args: dict) -> dict:
        code = str(args.get("code", ""))
        if not code.strip():
            return {"error": "code is required"}
        report = sandbox.run(code, args.get("data"))
        return {k: report[k] for k in
                ("ok", "result", "stdout", "error", "rejected_because",
                 "elapsed_s", "artifacts") if k in report}

    def _tool_document(self, args: dict) -> dict:
        fmt = str(args.get("format", "docx")).lower()
        maker = {"docx": outputs.make_docx, "pdf": outputs.make_pdf,
                "pptx": outputs.make_pptx}.get(fmt)
        if maker is None:
            return {"error": "format must be one of: docx, pdf, pptx"}
        title = str(args.get("title") or config.APP_NAME)
        content = str(args.get("content_markdown") or "")
        if not content.strip():
            return {"error": "content_markdown is required"}
        kwargs: dict[str, Any] = {}
        if fmt in ("pdf", "pptx") and args.get("image_paths"):
            kwargs["image_paths"] = args["image_paths"]
        rec = maker(title, content,
                   question=args.get("question") or self.last_question,
                   citations=self.last_citations, model=llm.chat_model(),
                   **kwargs)
        return {"ok": rec["ok"], "path": rec["path"],
                "filename": rec["filename"], "size_kb": rec["size_kb"]}

    def _tool_xlsx(self, args: dict) -> dict:
        title = str(args.get("title") or config.APP_NAME)
        table = args.get("table")
        if not table:
            return {"error": "table is required (a list of row objects, or "
                             "a list of lists with the header first)"}
        rec = outputs.make_xlsx(
            title, table, question=self.last_question,
            citations=self.last_citations, model=llm.chat_model(),
            chart=args.get("chart"), notes=str(args.get("notes") or ""))
        return {"ok": rec["ok"], "path": rec["path"],
                "filename": rec["filename"], "size_kb": rec["size_kb"]}

    def _tool_chart(self, args: dict) -> dict:
        title = str(args.get("title") or config.APP_NAME)
        x, series = args.get("x"), args.get("series")
        if not x or not series:
            return {"error": "x and series are required"}
        rec = outputs.make_chart(
            title, x, series, y_label=str(args.get("y_label") or ""),
            x_label=str(args.get("x_label") or ""), hlines=args.get("hlines"),
            question=self.last_question, kind=str(args.get("kind") or "line"))
        return {"ok": rec["ok"], "path": rec["path"],
                "filename": rec["filename"], "size_kb": rec["size_kb"]}


# ---------------------------------------------------------------------------
# Whole-system status, for the app's sidebar / setup screen
# ---------------------------------------------------------------------------
def system_status() -> dict:
    """Everything the setup screen needs in one call, so app.py does not have
    to know which core module owns which fact."""
    from core import netguard
    return {
        "config": config.describe(),
        "llm": llm.health(),
        "kb": kb.info(),
        "airgap": netguard.status(),
        "audit": audit.stats(),
    }
