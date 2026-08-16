#!/usr/bin/env python3
"""Print a temporary AO evidence brief for local packet authoring.

The page is fetched and parsed in memory. Nothing from the source page is
written into the repository; authored packets must contain original synthesis.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import urllib.request
from html.parser import HTMLParser
from typing import Any, Iterable

USER_AGENT = "SnapOrthoApproachAuthoring/1.0 (+local-evidence-review)"


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", html.unescape(" ".join(self.parts))).strip()


def _text(value: str) -> str:
    parser = TextParser()
    parser.feed(value)
    return parser.text()


def _walk(value: Any, heading: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        fields = value.get("fields") or {}
        headline = fields.get("headline")
        if isinstance(headline, dict) and str(headline.get("value") or "").strip():
            heading = _text(str(headline["value"]))
        subheadline = fields.get("subHeadline")
        paragraph = fields.get("paragraph")
        fragments = []
        for item in (subheadline, paragraph):
            if isinstance(item, dict) and str(item.get("value") or "").strip():
                fragments.append(_text(str(item["value"])))
        if fragments:
            yield heading or "Unheaded section", " ".join(fragments)
        for child in value.values():
            yield from _walk(child, heading)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child, heading)


def read_brief(url: str) -> list[tuple[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        page = response.read().decode("utf-8", errors="replace")
    match = re.search(
        r'<script type="application/json" id="__JSS_STATE__">(.*?)</script>', page, re.S
    )
    if not match:
        raise ValueError("AO structured page state was not found")
    state = json.loads(match.group(1))
    rows = []
    seen = set()
    for row in _walk(state):
        if row not in seen:
            rows.append(row)
            seen.add(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args()
    if not args.url.startswith("https://surgeryreference.aofoundation.org/"):
        raise SystemExit("Only AO Surgery Reference URLs are accepted")
    for heading, text in read_brief(args.url):
        print(f"[{heading}]\n{text}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
