#!/usr/bin/env python3
"""
Phase 1 test harness for local Miller gold anatomy retriever + builder.

Runs the 9 canonical orthopaedic case queries, prints retrieval + structured output,
and writes reports/.

Does NOT require the FastAPI server or the ENABLE flag (directly exercises the modules).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure we can import from root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from anatomy_retriever import get_anatomy_chunks, get_anatomy_retrieval_info
from anatomy_context_builder import build_anatomy_context

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

CASES: List[str] = [
    "distal radius fracture volar approach",
    "carpal tunnel release",
    "posterior total hip arthroplasty",
    "total knee arthroplasty medial parapatellar approach",
    "ACL reconstruction",
    "rotator cuff repair",
    "ankle ORIF lateral malleolus",
    "cubital tunnel release",
    "acetabular fracture ilioinguinal approach",
]

def run_one(query: str) -> Dict[str, Any]:
    print(f"\n=== {query} ===")
    chunks = get_anatomy_chunks(query, top_k=10)
    print(f"Retrieved {len(chunks)} chunks (after filter/boost)")

    for i, c in enumerate(chunks[:5], 1):
        print(f"  {i}. {c['id']} score={c['score']:.3f} page={c.get('page')} qt={c.get('quality_tier')}")
        preview = (c.get('text') or "")[:110].replace("\n", " ")
        print(f"     text: {preview}...")

    ctx = build_anatomy_context(chunks, case_prompt=query)

    limited = ctx.get("limitedAnatomyContext", False)
    print(f"  limitedAnatomyContext={limited}")
    print(f"  relevantAnatomy={len(ctx.get('relevantAnatomy', []))}")
    print(f"  structuresAtRisk={len(ctx.get('structuresAtRisk', []))}")
    print(f"  sources={len(ctx.get('sources', []))}")

    return {
        "query": query,
        "retrieved_count": len(chunks),
        "chunks": [
            {
                "id": c["id"],
                "score": c["score"],
                "raw_score": c.get("raw_score"),
                "page": c.get("page"),
                "region": c.get("region"),
                "subregion": c.get("subregion"),
                "quality_tier": c.get("quality_tier"),
                "text_preview": (c.get("text") or "")[:160],
                "source_quote_preview": (c.get("source_quote") or "")[:160],
            }
            for c in chunks
        ],
        "anatomy_context": ctx,
    }

def main():
    print("Local anatomy retriever info:", get_anatomy_retrieval_info())

    results: List[Dict[str, Any]] = []
    for q in CASES:
        try:
            res = run_one(q)
            results.append(res)
        except Exception as e:
            print(f"ERROR on '{q}': {e}")
            results.append({"query": q, "error": str(e)})

    # Write JSON
    json_path = REPORTS_DIR / "local_anatomy_rag_phase1_test_results.json"
    json_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "corpus": "anatomy_gold_v1_pinecone_ready (717 records)",
                "embedding_model": "text-embedding-3-small",
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n📄 Wrote JSON: {json_path}")

    # Write Markdown summary
    md_lines = [
        "# Local Anatomy RAG Phase 1 – Test Results",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Corpus: 717 records from anatomy_gold_v1_pinecone_ready.jsonl",
        "Embed model: text-embedding-3-small (matches production)",
        "Retriever: cosine + post-filter (min_score, dedupe, quality boost, region soft boost)",
        "",
        "## Per-Case Summary",
        "",
    ]

    for r in results:
        q = r.get("query", "?")
        if "error" in r:
            md_lines.append(f"### {q}\n\n**ERROR**: {r['error']}\n")
            continue

        ctx = r["anatomy_context"]
        limited = ctx.get("limitedAnatomyContext")
        md_lines.append(f"### {q}")
        md_lines.append(f"- retrieved: {r['retrieved_count']}")
        md_lines.append(f"- limitedAnatomyContext: {limited}")
        md_lines.append(f"- relevantAnatomy: {len(ctx.get('relevantAnatomy', []))}")
        md_lines.append(f"- structuresAtRisk: {len(ctx.get('structuresAtRisk', []))}")
        md_lines.append(f"- approachLandmarks: {len(ctx.get('approachLandmarks', []))}")
        md_lines.append(f"- highYieldFacts: {len(ctx.get('highYieldFacts', []))}")
        md_lines.append(f"- sources: {len(ctx.get('sources', []))}")
        if ctx.get("sources"):
            md_lines.append("  - " + "\n  - ".join(ctx["sources"][:3]))
        md_lines.append("")

        # top chunks
        md_lines.append("**Top chunks (score, page, preview):**")
        for c in r["chunks"][:3]:
            md_lines.append(f"- {c['score']:.3f} p.{c.get('page')} {c.get('id')}: {c['text_preview'][:90]}...")
        md_lines.append("")

    md_path = REPORTS_DIR / "local_anatomy_rag_phase1_test_results.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"📄 Wrote MD: {md_path}")

    print("\n✅ Phase 1 test harness complete.")

if __name__ == "__main__":
    main()
