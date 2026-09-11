"""
config.py — every knob for the whole workbench lives here.

If something needs changing (model name, a limit, a folder), change it HERE.
No other file should need editing for normal configuration.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Folders (created automatically on import)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCUMENTS = DATA / "documents"          # the corpus
UPLOADS = DATA / "uploads"              # documents added at demo time
INDEX = DATA / "index"                  # knowledge base files
EVAL = DATA / "eval"                    # golden question set
GENERATED = DATA / "generated"          # docx/xlsx/pptx/png the agent produces
LOGS = DATA / "logs"                    # hash-chained audit trail
SANDBOX = DATA / "sandbox"              # scratch space for executed code

for _p in (DATA, DOCUMENTS, UPLOADS, INDEX, EVAL, GENERATED, LOGS, SANDBOX):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Ollama — the local model server
# ---------------------------------------------------------------------------
# Loopback only. If this is ever pointed at a non-local address the air-gap
# guard in core/netguard.py will refuse to start.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_TIMEOUT = 300          # seconds; first call after a cold start is slow

# Main reasoning + tool-calling model.
# Primary choice: qwen2.5:7b-instruct  (Apache-2.0, reliable tool calling)
# Backup:         llama3.1:8b          (also good at tool calling in Ollama)
# Small fallback: qwen2.5:3b-instruct  (if VRAM is tight or the laptop is shared)
CHAT_MODEL = os.environ.get("SIH_CHAT_MODEL", "qwen2.5:7b-instruct")
CHAT_MODEL_FALLBACKS = ["llama3.1:8b", "qwen2.5:3b-instruct", "qwen2.5:7b"]

# Embeddings. Small enough to run on CPU, which keeps VRAM free for the LLM.
EMBED_MODEL = os.environ.get("SIH_EMBED_MODEL", "nomic-embed-text")
EMBED_DIM_HINT = 768

# Vision model, used ONLY for images and only when asked. Loaded on demand and
# unloaded immediately afterwards so it never shares VRAM with the chat model.
VISION_MODEL = os.environ.get("SIH_VISION_MODEL", "moondream")
VISION_MODEL_FALLBACKS = ["llava:7b", "qwen2.5vl:7b", "minicpm-v"]

# Generation settings
TEMPERATURE = 0.1             # low: we want faithful extraction, not prose
NUM_CTX = 8192                # context window; raise only if VRAM allows
NUM_PREDICT = 1400            # max tokens in a reply

# VRAM discipline. With 8-12 GB shared across a team, never hold two models.
SEQUENTIAL_MODEL_LOADING = True
KEEP_ALIVE = "5m"             # how long Ollama holds a model after last use
KEEP_ALIVE_RELEASE = 0        # value used to force-unload a model

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
CHUNK_TARGET_WORDS = 220      # a chunk is roughly a paragraph or table block
CHUNK_OVERLAP_WORDS = 45
RETRIEVE_K = 6                # chunks handed to the model per search
RETRIEVE_CANDIDATES = 30      # candidates considered before fusion
RETRIEVE_PER_DOC_CAP = 3      # max chunks from one document in a focused search
RRF_K = 60                    # reciprocal-rank-fusion constant
TAG_BOOST = 2.0               # weight for an exact equipment-tag / doc-id match

# A refinery runs on identifiers like P-2104B, PSV-2141, SOP-CDU2-014,
# WO-26-15118, INC-2026-0042. Pure semantic search is bad at these; exact
# matching is essential. This pattern is what makes the hybrid search work.
TAG_PATTERN = r"\b(?:[A-Z]{1,5}-\d{2,4}(?:-\d{2,5})?[A-Z]?|[A-Z]{2,6}-[A-Z0-9]{2,8}-\d{2,4}|CAPA-\d{4}-\d|H\d-\d{2})\b"

# ---------------------------------------------------------------------------
# Document extraction
# ---------------------------------------------------------------------------
# If a PDF page yields fewer than this many characters of real text, treat the
# page as a scan and send it to OCR.
OCR_TRIGGER_CHARS = 90
OCR_DPI = 300                 # render resolution for OCR
OCR_LANG = "eng"
# Windows installs Tesseract here by default. Left as None = "find it on PATH".
TESSERACT_CMD = os.environ.get("SIH_TESSERACT_CMD") or None
TESSERACT_WINDOWS_GUESSES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

# ---------------------------------------------------------------------------
# Sandbox for agent-written code
# ---------------------------------------------------------------------------
SANDBOX_TIMEOUT = 25          # seconds of wall clock
SANDBOX_MEMORY_MB = 1024      # enforced on Linux/macOS; advisory on Windows
SANDBOX_MAX_OUTPUT = 20000    # characters of stdout kept

# Only these modules can be imported by generated code. Anything else raises
# before it can run. Deliberately excludes os, sys, subprocess, socket,
# shutil, requests, urllib.
SANDBOX_ALLOWED_IMPORTS = {
    "math", "statistics", "json", "csv", "re", "datetime", "decimal",
    "fractions", "itertools", "functools", "collections", "textwrap",
    "random", "string", "typing", "dataclasses", "enum", "copy", "heapq",
    "bisect", "operator", "numbers", "time",
    "pandas", "numpy", "openpyxl", "matplotlib", "mpl_toolkits",
    "pandas._libs", "numpy._core",
}

# ---------------------------------------------------------------------------
# Human-in-the-loop approval gate
# ---------------------------------------------------------------------------
# When True, any tool marked requires_approval pauses and waits for a click.
# Leave this ON for the demo: it is one of the differentiators.
REQUIRE_APPROVAL = True

# ---------------------------------------------------------------------------
# Air-gap enforcement
# ---------------------------------------------------------------------------
# When True, this process physically cannot open a socket to anything except
# loopback. Any attempt is blocked and recorded in the audit trail.
ENFORCE_AIRGAP = True
AIRGAP_ALLOWED_HOSTS = {"127.0.0.1", "::1", "localhost", "0.0.0.0", ""}

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------
MAX_AGENT_STEPS = 8           # hard stop, so a confused model cannot spin
MAX_TOOL_RESULT_CHARS = 6000  # truncate a tool result before feeding it back

# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------
AUDIT_FILE = LOGS / "audit_chain.jsonl"
AUDIT_ENABLED = True

# ---------------------------------------------------------------------------
# Branding for generated documents
# ---------------------------------------------------------------------------
APP_NAME = "Sovereign AI Workbench"
APP_SUBTITLE = "On-premise agentic document intelligence"
PROBLEM_ID = "SIH26117"
ORG = "Mangalore Refinery and Petrochemicals Limited"
OUTPUT_FOOTER = (
    "Generated on-premise by the Sovereign AI Workbench. No data left this "
    "machine. Source documents are synthetic prototype data."
)


def describe() -> dict:
    """Configuration summary, shown in the UI so nothing is hidden."""
    return {
        "chat_model": CHAT_MODEL,
        "embed_model": EMBED_MODEL,
        "vision_model": VISION_MODEL,
        "ollama_host": OLLAMA_HOST,
        "sequential_model_loading": SEQUENTIAL_MODEL_LOADING,
        "airgap_enforced": ENFORCE_AIRGAP,
        "approval_gate": REQUIRE_APPROVAL,
        "retrieve_k": RETRIEVE_K,
        "chunk_words": CHUNK_TARGET_WORDS,
        "sandbox_timeout_s": SANDBOX_TIMEOUT,
        "max_agent_steps": MAX_AGENT_STEPS,
    }
