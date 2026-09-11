"""
core/audit.py — tamper-evident, append-only audit trail.

Why this exists: a refinery is a regulated environment. "The AI told me to do
X" is only defensible if you can show, afterwards, exactly what the AI was
asked, what it read, what it computed and who approved it — and prove the
record was not edited later.

Each record stores the SHA-256 of (previous record hash + this record's
content). Change or delete any record and every hash after it stops matching,
which verify() detects and reports. This is the same idea a blockchain uses,
without any of the machinery.

Nothing here needs a server, a database, or the network. It is one JSONL file.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

_LOCK = threading.Lock()
GENESIS = "0" * 64

# One id per app run, so a demo session can be filtered out of the log later.
SESSION_ID = uuid.uuid4().hex[:12]
_SESSION_START = time.time()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _canonical(obj: Any) -> str:
    """Stable JSON so the same content always hashes to the same value."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, default=str)


def _hash(prev_hash: str, body: dict) -> str:
    return hashlib.sha256((prev_hash + _canonical(body)).encode("utf-8")).hexdigest()


def _last_record() -> dict | None:
    path = Path(config.AUDIT_FILE)
    if not path.exists() or path.stat().st_size == 0:
        return None
    # Read only the tail of the file rather than all of it.
    with path.open("rb") as fh:
        try:
            fh.seek(-8192, os.SEEK_END)
        except OSError:
            fh.seek(0)
        tail = fh.read().decode("utf-8", errors="replace")
    lines = [ln for ln in tail.splitlines() if ln.strip()]
    for ln in reversed(lines):
        try:
            return json.loads(ln)
        except json.JSONDecodeError:
            continue
    return None


def log(event: str, payload: dict | None = None, *, actor: str = "system") -> dict:
    """Append one event. Returns the written record (including its hash)."""
    if not config.AUDIT_ENABLED:
        return {}
    payload = payload or {}
    with _LOCK:
        prev = _last_record()
        prev_hash = prev["hash"] if prev else GENESIS
        seq = (prev["seq"] + 1) if prev else 1
        body = {
            "seq": seq,
            "ts": _now(),
            "session": SESSION_ID,
            "event": event,
            "actor": actor,
            "payload": payload,
            "prev_hash": prev_hash,
        }
        rec = dict(body)
        rec["hash"] = _hash(prev_hash, body)
        path = Path(config.AUDIT_FILE)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=True, default=str) + "\n")
            fh.flush()
            os.fsync(fh.fileno())     # survive a crash mid-demo
    return rec


def read_all(limit: int | None = None, session: str | None = None) -> list[dict]:
    path = Path(config.AUDIT_FILE)
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                out.append({"seq": -1, "event": "CORRUPT_LINE", "raw": ln[:400]})
                continue
            if session and rec.get("session") != session:
                continue
            out.append(rec)
    if limit:
        out = out[-limit:]
    return out


def verify() -> dict:
    """Recompute the whole chain. This is what you run in front of a judge."""
    path = Path(config.AUDIT_FILE)
    if not path.exists():
        return {"ok": True, "records": 0, "message": "No audit file yet.",
                "first_bad_seq": None}
    prev_hash = GENESIS
    n = 0
    expected_seq = 1
    with path.open("r", encoding="utf-8") as fh:
        for lineno, ln in enumerate(fh, 1):
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                return {"ok": False, "records": n, "first_bad_seq": None,
                        "message": f"Line {lineno} is not valid JSON. The log "
                                   f"has been edited or truncated."}
            body = {k: rec[k] for k in ("seq", "ts", "session", "event",
                                        "actor", "payload", "prev_hash")
                    if k in rec}
            if rec.get("prev_hash") != prev_hash:
                return {"ok": False, "records": n,
                        "first_bad_seq": rec.get("seq"),
                        "message": f"Record {rec.get('seq')} does not link to "
                                   f"the previous record. A record was "
                                   f"inserted, removed or reordered."}
            if _hash(prev_hash, body) != rec.get("hash"):
                return {"ok": False, "records": n,
                        "first_bad_seq": rec.get("seq"),
                        "message": f"Record {rec.get('seq')} content does not "
                                   f"match its hash. It was modified after "
                                   f"being written."}
            if rec.get("seq") != expected_seq:
                return {"ok": False, "records": n,
                        "first_bad_seq": rec.get("seq"),
                        "message": f"Sequence jumped: expected "
                                   f"{expected_seq}, found {rec.get('seq')}."}
            prev_hash = rec["hash"]
            expected_seq += 1
            n += 1
    return {"ok": True, "records": n, "first_bad_seq": None,
            "head_hash": prev_hash,
            "message": f"Chain intact. {n} records verified, "
                       f"head {prev_hash[:16]}..."}


def stats() -> dict:
    recs = read_all()
    by_event: dict[str, int] = {}
    for r in recs:
        by_event[r.get("event", "?")] = by_event.get(r.get("event", "?"), 0) + 1
    sess = [r for r in recs if r.get("session") == SESSION_ID]
    return {
        "total_records": len(recs),
        "this_session": len(sess),
        "session_id": SESSION_ID,
        "by_event": dict(sorted(by_event.items(), key=lambda kv: -kv[1])),
        "file": str(config.AUDIT_FILE),
        "size_kb": round(Path(config.AUDIT_FILE).stat().st_size / 1024, 1)
        if Path(config.AUDIT_FILE).exists() else 0.0,
    }


def log_session_start() -> dict:
    return log("session.start", {
        "app": config.APP_NAME,
        "problem_id": config.PROBLEM_ID,
        "host": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "config": config.describe(),
    })


def export_report() -> str:
    """Plain-text audit report, for pasting into a slide or handing over."""
    v = verify()
    s = stats()
    lines = [
        "AUDIT TRAIL VERIFICATION REPORT",
        "=" * 62,
        f"File            : {s['file']}",
        f"Records         : {s['total_records']}  ({s['this_session']} this session)",
        f"Chain integrity : {'INTACT' if v['ok'] else 'BROKEN'}",
        f"Detail          : {v['message']}",
        "",
        "Events recorded:",
    ]
    for k, n in s["by_event"].items():
        lines.append(f"  {n:5d}  {k}")
    lines += [
        "",
        "Each record is hashed together with the hash of the record before it.",
        "Editing, deleting or reordering any record breaks every hash that",
        "follows, which the verification above detects.",
    ]
    return "\n".join(lines)
