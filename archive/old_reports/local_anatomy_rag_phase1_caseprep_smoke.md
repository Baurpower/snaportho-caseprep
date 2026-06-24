# Local Anatomy RAG Phase 1 – /case-prep Smoke Tests

**Date**: 2026-06-05
**Flag**: `ENABLE_LOCAL_ANATOMY_RAG=true`
**Method**: FastAPI TestClient (no external port/uvicorn needed for smoke)
**Corpus**: 717-record gold (anatomy_gold_v1_pinecone_ready)

## Results

### distal radius fracture volar approach
- status: 200
- pimpQuestions: 8
- otherUsefulFacts: 2
- anatomy.limitedAnatomyContext: false
- anatomy.retrievalMode: "miller_gold_local"
- anatomy.sources (count=3, first): "Miller p.33: An approach through the radial aspect of the FCR sheath: often easier and protects the radial artery"
- anatomy.relevantAnatomy (count=1)

### posterior total hip arthroplasty
- status: 200
- pimpQuestions: 5
- otherUsefulFacts: 4
- anatomy.limitedAnatomyContext: false
- anatomy.retrievalMode: "miller_gold_local"
- anatomy.sources (count=4, first): "Miller p.64: Particularly at risk for injury during psoas tenotomy through an anteromedial approach for developmental dysplasia of the hip"
- anatomy.relevantAnatomy (count=3)

### carpal tunnel release
- status: 200
- pimpQuestions: 4
- otherUsefulFacts: 5
- anatomy.limitedAnatomyContext: false
- anatomy.retrievalMode: "miller_gold_local"
- anatomy.sources (count=6, first): "Miller p.7: Transverse articulations between proximal and distal rows are reinforced by palmar and dorsal intercarpal ligaments and carpal..."
- anatomy.relevantAnatomy (count=8)

## Validation Notes
- No crashes.
- Existing pimpQuestions and otherUsefulFacts still populated (general RAG path unchanged).
- New Miller local anatomy path executed (retrievalMode, sources with page quotes, structured lists).
- limitedAnatomyContext=false for these in-scope cases.
- General retrieval logs showed some "non-anatomic" refiner behavior for CTR/distal-radius (expected; refiner is conservative), but Miller retriever still surfaced relevant chunks.
- Legacy path (flag=false) was not re-tested here but module-level print and prior code confirm it still loads anatomy_gpt.

See full test harness output in `local_anatomy_rag_phase1_test_results.md` (9 cases via direct modules).

No Pinecone calls, gold corpus untouched, OPENAI key values not printed.