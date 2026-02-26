import json
import re
from pathlib import Path

import pandas as pd


SECTION_HEADER_RE = re.compile(r"^[A-Z][A-Za-z ]+$")  # e.g., "Arm", "Hand", "Foot"


def _is_section_header(val: str) -> bool:
    s = str(val).strip()
    return bool(SECTION_HEADER_RE.match(s)) and "_" not in s


def _split_aliases(x):
    """
    Turn an alias cell into a list like ["lat", "lats"].
    Accepts comma/semicolon/pipe-separated.
    """
    if pd.isna(x):
        return []
    s = str(x).strip()
    if not s:
        return []
    parts = re.split(r"[;,|]\s*", s)
    return [p.strip() for p in parts if p and p.strip()]


def add_muscles_from_excel(
    metadata: dict,
    excel_path: str | Path,
    sheet_name: str = "bones",
    value_col: str | None = None,   # if None, uses first column
    aliases_col: str = "Aliases",
    add_alias_map: bool = True,     # adds "muscle_aliases" mapping if any aliases exist
) -> dict:
    excel_path = Path(excel_path)

    df = pd.read_excel(excel_path, sheet_name=sheet_name)

    if value_col is None:
        value_col = df.columns[0]  # first column (in your file it is "Shoulder")

    # Drop empty rows
    df = df.dropna(subset=[value_col])

    # Remove section header rows like "Arm", "Hand", etc.
    df = df[~df[value_col].astype(str).map(_is_section_header)]

    # Clean the slug strings
    slugs = (
        df[value_col]
        .astype(str)
        .str.strip()
        .replace({"": pd.NA})
        .dropna()
        .tolist()
    )

    # Deduplicate while preserving sheet order
    seen = set()
    ordered_slugs = []
    for s in slugs:
        if s not in seen:
            seen.add(s)
            ordered_slugs.append(s)

    # ---- merge into existing metadata without altering existing entries ----
    if "bones" not in metadata:
        metadata["bones"] = []

    existing = set(metadata["bones"])
    to_append = [s for s in ordered_slugs if s not in existing]
    metadata["bones"].extend(to_append)

    # Optional: build alias mapping (only if there are aliases)
    if add_alias_map and aliases_col in df.columns:
        alias_map = metadata.get("bone_aliases", {})
        any_aliases = False

        for _, row in df.iterrows():
            slug = str(row[value_col]).strip()
            if not slug or _is_section_header(slug):
                continue

            aliases = _split_aliases(row.get(aliases_col))
            if not aliases:
                continue

            any_aliases = True
            cur = alias_map.get(slug, [])
            # merge unique, preserve existing first
            cur_set = set(cur)
            for a in aliases:
                if a not in cur_set:
                    cur.append(a)
                    cur_set.add(a)
            alias_map[slug] = cur

        if any_aliases:
            metadata["muscle_aliases"] = alias_map

    return metadata


if __name__ == "__main__":
    # ---- paths you set ----
    METADATA_JSON_IN = "metadata_dictionary.updated2.json"      # your existing json on disk
    EXCEL_FILE = "anatomy_terms.xlsx"                      # your uploaded xlsx
    METADATA_JSON_OUT = "metadata_dictionary.updated3.json"

    # load existing metadata
    with open(METADATA_JSON_IN, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # update with muscles from Muscle_final
    metadata = add_muscles_from_excel(
        metadata=metadata,
        excel_path=EXCEL_FILE,
        sheet_name="bones",
        value_col=None,           # first column
        aliases_col="Aliases",
        add_alias_map=True,
    )

    # write updated json
    with open(METADATA_JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"✅ Wrote: {METADATA_JSON_OUT}")
    print(f"Added bones: {len(metadata.get('bones', []))} total")