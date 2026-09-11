"""
core/chunker.py — turn extracted blocks into retrievable chunks.

Naive chunking ("every 500 characters") is why most RAG demos cite the wrong
page. Two things break it in refinery documents:

  * A numbered procedure step split down the middle becomes dangerous advice.
  * A table row separated from its header row becomes meaningless numbers.

So this chunker is structure-aware. It keeps section headings attached to their
body, never splits a table away from its header, never breaks a numbered step,
and records the page each chunk came from so a citation can say
"SOP-CDU2-014 Rev 4, page 3, step 7" instead of "a document".

Every chunk also carries the equipment tags and document ids found inside it.
That list is what the exact-match half of the hybrid search uses.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

import config

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(config.TAG_PATTERN)

# A heading looks like "3. PROCEDURE", "SECTION 4 - CONTROLS", "5.2 Alignment"
_HEADING_RE = re.compile(
    r"^\s*(?:"
    r"(?:SECTION\s+)?\d{1,2}(?:\.\d{1,2}){0,2}[.)]?\s+[A-Z][A-Za-z /&,'-]{2,70}"
    r"|[A-Z][A-Z /&,'()-]{6,70}"
    r")\s*:?\s*$"
)

# A numbered procedure step: "7. Close the suction valve" / "7) ..." / "Step 7:"
_STEP_RE = re.compile(r"^\s*(?:Step\s+)?(\d{1,2})\s*[.):]\s+\S")

# Bullets we should not split away from the line above.
_BULLET_RE = re.compile(r"^\s*(?:[-*•·]|\(?[a-z]\)|[ivx]{1,4}\))\s+\S")


def find_tags(text: str) -> list[str]:
    """Equipment tags, document ids and reference numbers inside a piece of text.

    Deliberately generous: a false positive costs one extra retrieval candidate,
    a false negative means the agent cannot find the pump it was asked about.
    """
    found = {m.group(0).upper() for m in _TAG_RE.finditer(text or "")}
    # Bare unit/stream numbers are noise; tags always contain a hyphen.
    return sorted(t for t in found if "-" in t and not t.isdigit())


def normalise_whitespace(text: str) -> str:
    text = text.replace(" ", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Rejoin words hyphenated across a line break, an OCR artefact.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    return text.strip()


# ---------------------------------------------------------------------------
# OCR tag repair
# ---------------------------------------------------------------------------
# A scan of a paper form will hand you "P-21(4A" where the page clearly says
# "P-2104A". Left alone, the exact-match half of the search silently misses that
# mention - the worst kind of failure, because the answer still looks complete.
#
# So for OCR and vision text only, near-miss tags are repaired against the
# plant's own equipment register. Every correction is recorded and shown in the
# UI: silently rewriting the text of a source document would be indefensible in
# a regulated environment.

# Character confusions Tesseract actually makes, mapped to what a tag can hold.
_OCR_FIX = str.maketrans({
    "O": "0", "o": "0", "Q": "0", "D": "0", "(": "0", ")": "0",
    "l": "1", "I": "1", "|": "1", "!": "1", "i": "1",
    "Z": "2", "z": "2",
    "S": "5", "s": "5",
    "G": "6", "b": "6",
    "T": "7",
    "B": "8",
    "g": "9", "q": "9",
})

# Something shaped like a tag, which may contain OCR damage.
_TAGLIKE_RE = re.compile(r"\b[A-Z]{1,5}[-–—][A-Za-z0-9()|!]{2,9}[A-Z]?\b")


def _tag_skeleton(tag: str) -> str:
    """Collapse a tag into a form where OCR-confusable characters agree."""
    prefix, _, rest = tag.partition("-")
    return prefix.upper() + "-" + rest.translate(_OCR_FIX).upper()


def repair_ocr_tags(text: str,
                    known_tags: Iterable[str]) -> tuple[str, list[dict]]:
    """Fix OCR-damaged equipment tags against a register of real tags.

    Rewrites only when the damaged token maps onto exactly one known tag, so it
    can never invent an item of equipment that does not exist. Returns the
    corrected text and a list of what changed.
    """
    known_upper = {t.upper() for t in known_tags}
    skeletons: dict[str, set[str]] = {}
    for t in known_upper:
        skeletons.setdefault(_tag_skeleton(t), set()).add(t)

    corrections: list[dict] = []
    seen: set[str] = set()

    def fix(match: "re.Match[str]") -> str:
        raw = match.group(0)
        candidate = raw.replace("–", "-").replace("—", "-")
        if candidate.upper() in known_upper:
            return raw                                  # already correct
        options = skeletons.get(_tag_skeleton(candidate))
        if not options or len(options) != 1:
            return raw                                  # ambiguous: leave alone
        fixed = next(iter(options))
        if raw != fixed:
            if raw not in seen:
                seen.add(raw)
                corrections.append({"from": raw, "to": fixed})
            return fixed
        return raw

    return _TAGLIKE_RE.sub(fix, text or ""), corrections


def is_heading(line: str) -> bool:
    line = line.strip()
    if not (3 <= len(line) <= 90):
        return False
    if line.endswith((".", ";", ",")):
        return False
    if len(line.split()) > 12:
        return False
    return bool(_HEADING_RE.match(line))


# ---------------------------------------------------------------------------
# Segmenting one block of prose into logical paragraphs
# ---------------------------------------------------------------------------
def _segments(text: str) -> list[dict]:
    """Split prose into units that must not be broken apart.

    A unit is a paragraph, or a numbered step together with any bullets and
    continuation lines beneath it.
    """
    lines = normalise_whitespace(text).split("\n")
    units: list[dict] = []
    current: list[str] = []
    current_kind = "para"
    heading = ""

    def flush():
        nonlocal current, current_kind
        body = "\n".join(current).strip()
        if body:
            units.append({"text": body, "kind": current_kind, "heading": heading})
        current = []
        current_kind = "para"

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        if is_heading(line):
            flush()
            heading = line.strip().rstrip(":")
            units.append({"text": line.strip(), "kind": "heading",
                          "heading": heading})
            continue
        if _STEP_RE.match(line):
            flush()
            current = [line]
            current_kind = "step"
            continue
        if current_kind == "step" and (_BULLET_RE.match(line)
                                       or line.startswith(("  ", "\t"))
                                       or line[:1].islower()):
            current.append(line)          # continuation of the same step
            continue
        if current_kind == "step":
            flush()
        current.append(line)
    flush()
    return units


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def chunk_blocks(blocks: list[dict], doc_meta: dict,
                 target_words: int | None = None,
                 overlap_words: int | None = None,
                 known_tags: Iterable[str] | None = None) -> list[dict]:
    """Convert extract.py blocks into chunks ready for indexing.

    A block is {"text", "page", "kind"} where kind is one of
    text | table | ocr | vision | sheet.

    Rules:
      * table / sheet blocks are never merged with prose and never split
        (their header row is part of the text already).
      * prose is packed up to target_words, breaking only at unit boundaries.
      * consecutive prose chunks overlap by overlap_words so a fact that
        straddles a boundary is still findable.
      * ocr / vision blocks get their equipment tags repaired against
        known_tags, and the corrections are reported back on the chunk.
      * every chunk gets a header line naming the document, page and section, so
        the model sees provenance inside the context, not only in metadata.
    """
    target = target_words or config.CHUNK_TARGET_WORDS
    overlap = overlap_words or config.CHUNK_OVERLAP_WORDS
    register = list(known_tags or [])

    chunks: list[dict] = []
    all_corrections: list[dict] = []
    buf: list[dict] = []          # units waiting to be emitted
    buf_words = 0
    buf_pages: set[int] = set()
    section = ""

    def emit(kind: str = "text") -> None:
        nonlocal buf, buf_words, buf_pages
        if not buf:
            return
        body = "\n".join(u["text"] for u in buf).strip()
        if len(body.split()) < 5 and kind == "text":
            buf, buf_words, buf_pages = [], 0, set()
            return
        pages = sorted(buf_pages) or [doc_meta.get("page", 1)]
        sec = next((u["heading"] for u in reversed(buf) if u.get("heading")),
                   section)
        chunks.append(_make_chunk(body, doc_meta, pages, sec, kind))
        # carry the tail forward as overlap
        if overlap > 0 and kind == "text":
            tail_words: list[str] = []
            carry: list[dict] = []
            for u in reversed(buf):
                w = u["text"].split()
                if len(tail_words) + len(w) > overlap and tail_words:
                    break
                tail_words = w + tail_words
                carry.insert(0, u)
            buf = carry
            buf_words = len(tail_words)
            buf_pages = {p for p in pages[-1:]}
        else:
            buf, buf_words, buf_pages = [], 0, set()

    for block in blocks:
        text = (block.get("text") or "").strip()
        if not text:
            continue
        kind = block.get("kind", "text")
        page = int(block.get("page") or 1)

        # Repair OCR-damaged tags before anything indexes them.
        if kind in ("ocr", "vision") and register:
            text, fixes = repair_ocr_tags(text, register)
            all_corrections.extend(fixes)

        if kind in ("table", "sheet"):
            emit()                                  # close open prose first
            for part in _split_table(text, target):
                chunks.append(_make_chunk(part, doc_meta, [page],
                                          block.get("section") or section,
                                          kind))
            continue

        for unit in _segments(text):
            if unit["kind"] == "heading":
                section = unit["heading"]
                # A heading belongs with what follows it, so start a new chunk.
                if buf_words > target * 0.6:
                    emit()
                buf.append(unit)
                buf_pages.add(page)
                continue
            w = len(unit["text"].split())
            if buf_words + w > target and buf_words > 0:
                emit()
            buf.append(unit)
            buf_words += w
            buf_pages.add(page)
            if unit["kind"] == "step" and buf_words > target * 1.4:
                emit()

    emit()

    for i, c in enumerate(chunks):
        c["chunk_index"] = i
        c["chunk_id"] = f"{doc_meta.get('doc_id', 'DOC')}::c{i:03d}"
    if all_corrections and chunks:
        # Deduplicate and attach to the document's first chunk so the ingest
        # report and the UI can surface exactly what was corrected.
        uniq = {(f["from"], f["to"]) for f in all_corrections}
        chunks[0]["ocr_tag_corrections"] = [
            {"from": a, "to": b} for a, b in sorted(uniq)]
    return chunks


def _split_table(text: str, target: int) -> list[str]:
    """Split a long table on row boundaries, repeating the header each time."""
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if not lines:
        return []
    if len(text.split()) <= target * 1.6:
        return [text]
    # Assume the first one or two lines are title/header material.
    header_n = 2 if len(lines) > 3 and "|" in lines[0] and "|" in lines[1] else 1
    header = lines[:header_n]
    rows = lines[header_n:]
    out, cur, cur_w = [], [], 0
    head_w = len(" ".join(header).split())
    for row in rows:
        w = len(row.split())
        if cur and head_w + cur_w + w > target:
            out.append("\n".join(header + cur))
            cur, cur_w = [], 0
        cur.append(row)
        cur_w += w
    if cur:
        out.append("\n".join(header + cur))
    return out


def _make_chunk(body: str, doc_meta: dict, pages: list[int], section: str,
                kind: str) -> dict:
    doc_id = doc_meta.get("doc_id", "DOC")
    title = doc_meta.get("title", "")
    loc = f"page {pages[0]}" if len(pages) == 1 else f"pages {pages[0]}-{pages[-1]}"
    if kind == "sheet":
        loc = f"sheet {section}" if section else loc
    header = f"[{doc_id} | {title} | {loc}"
    if section and kind != "sheet":
        header += f" | section: {section}"
    header += "]"
    text_for_model = header + "\n" + body

    tags = find_tags(body)
    # The document's own id should always be searchable inside its chunks.
    if doc_id and doc_id not in tags:
        tags.append(doc_id)

    return {
        "doc_id": doc_id,
        "title": title,
        "filename": doc_meta.get("filename", ""),
        "doc_type": doc_meta.get("doc_type", ""),
        "page_start": pages[0],
        "page_end": pages[-1],
        "section": section,
        "kind": kind,
        "text": text_for_model,
        "body": body,
        "tags": sorted(set(tags)),
        "word_count": len(body.split()),
        "citation": citation_for(doc_id, title, pages, section, kind),
    }


def citation_for(doc_id: str, title: str, pages: list[int], section: str,
                 kind: str) -> str:
    """The exact string the model is told to cite, and the UI renders."""
    if kind == "sheet":
        return f"{doc_id}, sheet '{section}'" if section else doc_id
    where = f"p.{pages[0]}" if len(pages) == 1 else f"pp.{pages[0]}-{pages[-1]}"
    if section:
        short = section if len(section) <= 40 else section[:37] + "..."
        return f"{doc_id} {where} ({short})"
    return f"{doc_id} {where}"


def stats(chunks: Iterable[dict]) -> dict[str, Any]:
    chunks = list(chunks)
    if not chunks:
        return {"chunks": 0}
    wc = [c["word_count"] for c in chunks]
    kinds: dict[str, int] = {}
    for c in chunks:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    return {
        "chunks": len(chunks),
        "words_total": sum(wc),
        "words_mean": round(sum(wc) / len(wc), 1),
        "words_min": min(wc),
        "words_max": max(wc),
        "by_kind": kinds,
        "with_tags": sum(1 for c in chunks if len(c["tags"]) > 1),
        "distinct_tags": len({t for c in chunks for t in c["tags"]}),
    }
