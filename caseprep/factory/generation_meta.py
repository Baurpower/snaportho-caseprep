"""Read/write generation_meta.json artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from caseprep.factory.schemas import GenerationMeta


def load_generation_meta(path: Path) -> Optional[GenerationMeta]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return GenerationMeta.model_validate(json.load(handle))


def write_generation_meta(path: Path, meta: GenerationMeta) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(meta.model_dump(), handle, indent=2, ensure_ascii=False)
        handle.write("\n")