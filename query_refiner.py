import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Load controlled vocab ---
DICT_PATH = Path("metadata_dictionary.json")
with open(DICT_PATH, "r", encoding="utf-8") as f:
    META_DICT = json.load(f)

REGIONS    = META_DICT.get("regions", [])
SUBREGIONS = META_DICT.get("subregions", [])
DIAGNOSES  = META_DICT.get("diagnoses", [])
PROCEDURES = META_DICT.get("procedures", [])

SPECIALTIES = [
    "trauma", "sports", "recon", "hand", "peds",
    "spine", "onc", "footankle", "shoulderelbow", "basicscience"
]

import re

EXPANSIONS = {
    # procedures
    r"\bcrpp\b": "closed reduction percutaneous pinning",
    r"\bctr\b": "carpal tunnel release",
    r"\bpsf\b": "posterior spinal fusion",
    r"\brsa\b|\brtsa\b": "reverse shoulder arthroplasty",
    r"\btsa\b": "shoulder arthroplasty total shoulder arthroplasty",
    r"\bha\b": "hemiarthroplasty",
    r"\bdhs\b": "sliding hip screw",
    r"\bshs\b": "sliding hip screw",
    r"\bim\s*nail\b": "intramedullary nail",
    r"\bimn\b": "intramedullary nail",
    r"\bex[-\s]?fix\b": "external fixation external fixator",

    # already-have core ones (keep)
    r"\btha\b": "total hip arthroplasty",
    r"\btka\b": "total knee arthroplasty",
    r"\buka\b": "unicompartmental knee arthroplasty",
    r"\borif\b": "open reduction internal fixation",
    r"\bfx\b": "fracture",
    r"\bpji\b": "periprosthetic joint infection",

    # diagnoses / conditions
    r"\bddh\b": "developmental dysplasia of the hip",
    r"\bscfe\b": "slipped capital femoral epiphysis",
    r"\bfai\b": "femoroacetabular impingement",
    r"\bdish\b": "diffuse idiopathic skeletal hyperostosis",
    r"\bptti\b": "posterior tibial tendon insufficiency",
    r"\boa\b": "osteoarthritis",

    # subregions / anatomy
    r"\bacj\b": "ac joint",
    r"\bscj\b": "sc joint",
    r"\bdruj\b": "distal radioulnar joint DRUJ",
    r"\btfcc\b": "triangular fibrocartilage complex TFCC",
    r"\bacl\b": "anterior cruciate ligament ACL",
    r"\bpcl\b": "posterior cruciate ligament PCL",
    r"\bmcl\b": "medial collateral ligament MCL",
    r"\blcl\b": "lateral collateral ligament LCL",
    r"\bplc\b": "posterolateral corner PLC",
}

def build_search_text(user_prompt: str) -> str:
    base = user_prompt.strip()
    p = base.lower()

    extras = []
    for pat, repl in EXPANSIONS.items():
        if re.search(pat, p):
            extras.append(repl)

    # Keep it simple: original + extras appended
    return base if not extras else base + " | " + " | ".join(extras)

def guess_region(prompt: str) -> str:
    p = prompt.lower()
    # crude but effective
    if any(w in p for w in ["hip", "tha", "acetabul", "femoral neck", "intertroch", "subtroch"]): return "hip"
    if any(w in p for w in ["knee", "tka", "uka", "tibial plateau", "acl", "meniscus"]): return "knee"
    if any(w in p for w in ["ankle", "pilon", "talus", "calcane", "achilles"]): return "ankle"
    if any(w in p for w in ["foot", "lisfranc", "metatarsal", "hallux"]): return "foot"
    if any(w in p for w in ["wrist", "distal radius", "scaphoid", "tfcc"]): return "wrist"
    if any(w in p for w in ["hand", "metacarp", "phalange", "trigger"]): return "hand"
    if any(w in p for w in ["elbow", "olecranon", "radial head"]): return "elbow"
    if any(w in p for w in ["shoulder", "proximal humerus", "rotator cuff", "labrum"]): return "shoulder"
    if any(w in p for w in ["spine", "cervical", "thoracic", "lumbar"]): return "spine"
    if any(w in p for w in ["pelvis", "sacrum", "iliac", "pelvic ring"]): return "pelvis"
    if any(w in p for w in ["tibia", "fibula", "leg"]): return "leg"
    if any(w in p for w in ["femur", "thigh"]): return "thigh"
    if any(w in p for w in ["humerus", "arm"]): return "arm"
    if any(w in p for w in ["forearm", "radius", "ulna"]): return "forearm"
    return "non-anatomic"

def _build_system_prompt(diag_sample: str, proc_sample: str) -> str:
    return f"""
You are an expert orthopaedic surgeon educator building CANONICAL metadata tokens for a vector database.

You MUST follow the controlled vocab and rules.
If unsure about an exact slug for diagnosis/procedure, return an empty list for that field.

SPECIALTIES (choose 1–2 ONLY):
{", ".join(SPECIALTIES)}

SPECIALTY RULES (follow strictly):
- Any elbow case MUST include BOTH shoulderelbow and hand.
- Any spine case MUST include spine.
- Any hand case MUST include hand.
- Any shoulder case MUST include shoulderelbow.
- Any acute fracture fixation case (fx/fracture OR ORIF/IM nail/ex-fix) MUST include trauma.
- Any case with tha or tka (including periprosthetic fxs and revisions) MUST include recon.

DIAGNOSIS AND PROCEDURE RULES:
- For diagnoses and procedures, ONLY output a slug if the user prompt contains specific keywords that unambiguously support that exact slug.
- If the prompt is missing the specific keyword(s) for an exact slug, return an empty list for that field.
- Do NOT “upgrade” a generic term to a specific diagnosis/procedure.
- When in doubt, leave diagnoses/procedures blank. False negatives are preferred over false positives.


CANONICAL TOKENS:
- region: exactly one of: {", ".join(REGIONS)}
- subregion: optional, but if used must be exactly one of: {", ".join(SUBREGIONS)}
- diagnoses: 0–3 slugs from diagnoses vocabulary (snake_case). Examples: {diag_sample}
- procedures: 0–3 slugs from procedures vocabulary (snake_case). Examples: {proc_sample}

Return STRICT JSON ONLY (no markdown, no commentary) matching this schema:
{{
  "specialties": ["trauma"],
  "region": "thigh",
  "subregion": "femoral_shaft",
  "diagnoses": ["femoral_shaft_fx"],
  "procedures": ["femoral_shaft_orif"]
}}
""".strip()

def _empty_payload_for(prompt: str, search_text: str) -> dict:
    # safest possible payload that won't nuke your filters
    return {
        "specialties": ["trauma"] if ("fx" in prompt.lower() or "fracture" in prompt.lower()) else ["recon"],
        "region": "non-anatomic",   # use something valid from REGIONS
        "subregion": "",
        "diagnoses": [],
        "procedures": [],
        "search_text": search_text,
        "raw_prompt": prompt.strip(),
    }

def coerce_payload(payload: dict, search_text: str, raw_prompt: str) -> dict:
    # ensure required keys exist
    payload = payload if isinstance(payload, dict) else {}
    payload.setdefault("specialties", [])
    payload.setdefault("region", "")
    payload.setdefault("subregion", "")
    payload.setdefault("diagnoses", [])
    payload.setdefault("procedures", [])

    # specialties: string -> [string]
    if isinstance(payload["specialties"], str):
        payload["specialties"] = [payload["specialties"]]

    # diagnoses/procedures: string -> [string]
    if isinstance(payload["diagnoses"], str):
        payload["diagnoses"] = [payload["diagnoses"]]
    if isinstance(payload["procedures"], str):
        payload["procedures"] = [payload["procedures"]]

    # trim list lengths
    if isinstance(payload["diagnoses"], list):
        payload["diagnoses"] = payload["diagnoses"][:3]
    else:
        payload["diagnoses"] = []

    if isinstance(payload["procedures"], list):
        payload["procedures"] = payload["procedures"][:3]
    else:
        payload["procedures"] = []
    payload["diagnoses"]  = [d for d in payload["diagnoses"] if d in DIAGNOSES]
    payload["procedures"] = [p for p in payload["procedures"] if p in PROCEDURES]

    # enforce specialties length 1–2 and prioritize obvious ones if too long
    if not isinstance(payload["specialties"], list):
        payload["specialties"] = []
    else:
        priority = ["trauma", "recon", "spine", "hand", "shoulderelbow", "footankle", "sports", "peds", "onc", "basicscience"]
        ordered = [s for s in priority if s in payload["specialties"]] + [s for s in payload["specialties"] if s not in priority]
        payload["specialties"] = ordered[:2]

    # attach meta
    payload["search_text"] = search_text
    payload["raw_prompt"] = raw_prompt.strip()
    

    return payload

def _validate_payload(payload: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []

    # specialties
    specs = payload.get("specialties", [])
    if not isinstance(specs, list) or not (1 <= len(specs) <= 2):
        errors.append("specialties must be a list of length 1–2")
    else:
        bad = [s for s in specs if s not in SPECIALTIES]
        if bad:
            errors.append(f"invalid specialties: {bad}")

    # region
    region = payload.get("region")
    if region not in REGIONS:
        errors.append(f"region must be one of REGIONS (got {region})")

    # subregion
    subregion = payload.get("subregion", "")
    if subregion and subregion not in SUBREGIONS:
        errors.append(f"subregion must be blank or one of SUBREGIONS (got {subregion})")

    # diagnoses/procedures
    diagnoses = payload.get("diagnoses", [])
    procedures = payload.get("procedures", [])

    if not isinstance(diagnoses, list) or len(diagnoses) > 3:
        errors.append("diagnoses must be a list of length 0–3")
    else:
        bad = [d for d in diagnoses if d not in DIAGNOSES]
        if bad:
            errors.append(f"invalid diagnoses slugs: {bad}")

    if not isinstance(procedures, list) or len(procedures) > 3:
        errors.append("procedures must be a list of length 0–3")
    else:
        bad = [p for p in procedures if p not in PROCEDURES]
        if bad:
            errors.append(f"invalid procedures slugs: {bad}")

    return (len(errors) == 0, errors)

def refine_query(user_prompt: str) -> dict | str:
    if not user_prompt.strip():
        return ""

    search_text = build_search_text(user_prompt)

    # Reduce prompt bloat: 120 is unnecessary and increases formatting failures
    diag_sample = ", ".join(DIAGNOSES[:30])
    proc_sample = ", ".join(PROCEDURES[:30])
    system_prompt = _build_system_prompt(diag_sample, proc_sample)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt.strip()},
        ],
        temperature=0.0,
        max_tokens=220,
    )

    raw = resp.choices[0].message.content.strip()

    try:
        payload = json.loads(raw)
    except Exception:
        # If JSON parse fails, return safe payload instead of killing retrieval
        return _empty_payload_for(user_prompt, search_text)

    payload = coerce_payload(payload, search_text, user_prompt)

    ok, errors = _validate_payload(payload)
    if ok:
        return payload

    # If still invalid, return safe payload (do NOT return a string error)
    # Optional: print/log errors + raw for debugging
    # print("Refiner invalid:", errors, "raw:", raw)
    return _empty_payload_for(user_prompt, search_text)
def payload_to_csv_line(p: dict) -> str:
    fields = []
    fields += p.get("specialties", [])
    fields.append(p.get("region", ""))
    sub = p.get("subregion", "")
    if sub:
        fields.append(sub)
    fields += p.get("diagnoses", [])
    fields += p.get("procedures", [])
    fields = [f for f in fields if f]
    return ", ".join(fields)

if __name__ == "__main__":
    print("🧠 Ortho Prompt Refiner (canonical metadata)")
    while True:
        user_input = input("\nEnter a surgical case prompt (or 'q' to quit): ").strip()
        if user_input.lower() in {"q", "quit", "exit"}:
            break

        result = refine_query(user_input)

        if isinstance(result, dict):
            print("\n🛠️ Refined metadata payload:\n" + json.dumps(result, indent=2))
            print("\n🧾 CSV line:\n" + payload_to_csv_line(result))
        else:
            print("\n" + str(result))