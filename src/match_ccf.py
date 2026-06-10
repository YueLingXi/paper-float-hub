from __future__ import annotations

import re
from typing import Any


def _tokens(item: dict[str, Any]) -> set[str]:
    values = [item.get("abbr"), item.get("full_name"), *(item.get("aliases") or [])]
    return {re.sub(r"\s+", " ", str(v).lower()).strip() for v in values if v}


def attach_ccf_level(papers: list[dict[str, Any]], ccf_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = [(_tokens(item), item) for item in ccf_items]
    for paper in papers:
        venue = str(paper.get("venue") or "").lower().strip()
        haystack = " ".join([venue, str(paper.get("title") or "").lower(), str(paper.get("abstract") or "").lower()])
        paper["ccf_level"] = None
        paper["ccf_match"] = None
        for names, item in index:
            if (venue and venue in names) or any(name and re.search(rf"\b{re.escape(name)}\b", haystack) for name in names):
                paper["ccf_level"] = item.get("level")
                paper["ccf_match"] = item.get("abbr") or item.get("full_name")
                break
    return papers
