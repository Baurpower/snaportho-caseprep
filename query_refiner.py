# services/query_refiner.py
SYSTEM = """You are an ortho surgery librarian.
Rewrite the user’s short description into a *single* highly–specific search query.
Keep anatomy terms, fracture types, and laterality. Remove fluff."""
FEW_SHOTS = [
    ("38 y/o w/ fem neck fx", 
     "femoral neck fracture adult key anatomy pimp questions"),
    ("Tib plateau (Schatzker VI) pre-op", 
     "bicondylar tibial plateau fracture (Schatzker VI) key anatomy pimp questions pearls")
]

def refine(user_blurb: str, client):
    shots = [{"role":"user","content":u} for u,_ in FEW_SHOTS] + \
            [{"role":"assistant","content":a} for _,a in FEW_SHOTS]
    msgs  = [{"role":"system","content": SYSTEM}] + shots + \
            [{"role":"user","content": user_blurb}]
    out = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=msgs
    )
    return out.choices[0].message.content.strip()
