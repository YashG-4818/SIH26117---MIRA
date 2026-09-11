"""
make_corpus.py — run every corpus builder and write the manifest.

    python scripts/make_corpus.py

The manifest is what the knowledge base reads to attach a document id, title,
type and "why it exists in the demo" to every file. It is also what the Trust
tab uses to show corpus coverage.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import corpus_spec as S
import build_pdfs as P
import build_office as O
import build_scanned as C

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "documents"
EVAL = ROOT / "data" / "eval"
OUT.mkdir(parents=True, exist_ok=True)
EVAL.mkdir(parents=True, exist_ok=True)


BUILDERS = [
    # (builder, doc_key, doc_type, extraction_path, demo_purpose)
    (P.build_sop, "sop", "Standard Operating Procedure", "native_text",
     "The authoritative procedure. Tests whether the agent quotes a real "
     "numbered step instead of inventing one."),
    (P.build_incident, "incident", "Incident Investigation Report",
     "native_text",
     "The narrative centre of the corpus. Root cause, 5-why and CAPA table."),
    (P.build_hazop, "hazop", "HAZOP Action Register", "pdf_table",
     "Deliberately table-heavy so pdfplumber table extraction is exercised. "
     "Contains the overdue action the agent should surface unprompted."),
    (P.build_circular, "circular", "Safety Circular", "native_text",
     "Time-bounded restriction. Tests date-aware reasoning: is hot work "
     "allowed on a given date?"),
    (P.build_ops_report, "ops", "Monthly Operations Report", "native_text",
     "Numeric KPI tables plus narrative. Feeds the chart and report "
     "generation demo."),
    (P.build_std_summary, "std", "Engineering Practice Summary", "native_text",
     "The 'rule book' the agent measures the plant against, giving it "
     "something to reason with rather than only facts to recite."),
    (O.build_moc, "moc", "Management of Change", "docx",
     "DOCX path. Holds the approval status and the procurement blocker."),
    (O.build_vib_xlsx, "vib", "Condition Monitoring Log", "xlsx",
     "The numeric substrate for the sandbox calculation demo (trend slope, "
     "limit breaches). Includes an embedded chart."),
    (O.build_wo_xlsx, "wo", "Work Order History", "xlsx",
     "Maintenance history with cost and downtime. Supports 'has this happened "
     "before and what did it cost' questions."),
    (O.build_spares_xlsx, "spares", "Spares Inventory", "xlsx",
     "Where the punchline lives: the approved fix is blocked on a 45-day lead "
     "time. This is what makes the multi-hop answer feel intelligent."),
    (O.build_training_xlsx, "training", "Competency Matrix", "xlsx",
     "Date arithmetic against an as-of date. Tests whether the agent computes "
     "expiry rather than copying a cell."),
    (C.build_handover_scanned, "handover", "Shift Handover Log (scanned)",
     "ocr_image",
     "NO text layer. Skewed, speckled, hand-filled, JPEG-degraded. This is the "
     "OCR proof document and the one to show a sceptical judge."),
    (C.build_pid_png, "pid", "P&ID Flow Schematic", "vision",
     "Image-only engineering drawing for the vision-model branch."),
]


def main():
    print("=" * 74)
    print("Building the synthetic MRPL corpus for SIH26117")
    print("=" * 74)

    entries = []
    for builder, key, dtype, path_kind, purpose in BUILDERS:
        doc = S.DOCS[key]
        try:
            p = builder()
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {key:10s}  {type(exc).__name__}: {exc}")
            raise
        size_kb = p.stat().st_size / 1024
        entries.append({
            "doc_id": doc["id"],
            "title": doc["title"],
            "filename": p.name,
            "doc_type": dtype,
            "extraction_path": path_kind,
            "demo_purpose": purpose,
            "size_kb": round(size_kb, 1),
            "classification": S.PLANT["doc_class"],
            "unit": S.PLANT["unit_code"],
            "synthetic": True,
        })
        print(f"  ok    {doc['id']:20s} {p.name[:44]:46s} {size_kb:7.1f} KB")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "scripts/make_corpus.py",
        "plant": S.PLANT,
        "notice": (
            "Every document in this corpus is SYNTHETIC. It is modelled on real "
            "refinery document formats and is internally cross-consistent, but "
            "contains no actual MRPL data. State this openly when presenting."
        ),
        "document_count": len(entries),
        "equipment_register": S.EQUIPMENT,
        "documents": entries,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                       encoding="utf-8")

    golden = {
        "generated_at": manifest["generated_at"],
        "note": (
            "Retrieval and answer evaluation set. 'must_cite' lists the "
            "document ids a correct answer has to be grounded in; "
            "'must_contain' lists strings a correct answer should mention; "
            "'hops' is how many separate documents must be combined."
        ),
        "questions": S.GOLDEN_QUESTIONS,
    }
    (EVAL / "golden_questions.json").write_text(json.dumps(golden, indent=2),
                                                encoding="utf-8")

    print("-" * 74)
    print(f"  {len(entries)} documents -> {OUT}")
    print(f"  manifest        -> {OUT / 'manifest.json'}")
    print(f"  {len(S.GOLDEN_QUESTIONS)} eval questions -> "
          f"{EVAL / 'golden_questions.json'}")
    by_path = {}
    for e in entries:
        by_path[e["extraction_path"]] = by_path.get(e["extraction_path"], 0) + 1
    print("  extraction paths exercised: " +
          ", ".join(f"{k}={v}" for k, v in sorted(by_path.items())))
    print("=" * 74)


if __name__ == "__main__":
    main()
