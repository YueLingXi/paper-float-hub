from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

DEFAULT_ITEMS = [
    {"abbr": "ACL", "full_name": "Annual Meeting of the Association for Computational Linguistics", "type": "conference", "field": "Artificial Intelligence", "level": "A", "aliases": ["ACL", "Annual Meeting of the ACL"]},
    {"abbr": "NeurIPS", "full_name": "Conference on Neural Information Processing Systems", "type": "conference", "field": "Artificial Intelligence", "level": "A", "aliases": ["NIPS", "Neural Information Processing Systems"]},
    {"abbr": "EMNLP", "full_name": "Conference on Empirical Methods in Natural Language Processing", "type": "conference", "field": "Artificial Intelligence", "level": "B", "aliases": ["Empirical Methods in Natural Language Processing"]},
]


def _load_cached(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": "seed", "items": DEFAULT_ITEMS}
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_ccf_deadlines(raw: Any) -> list[dict[str, Any]]:
    rows = raw if isinstance(raw, list) else raw.get("conferences", []) if isinstance(raw, dict) else []
    items: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or row.get("name") or "").strip()
        desc = str(row.get("description") or row.get("full_name") or "").strip()
        rank = str(row.get("rank") or row.get("ccf") or row.get("level") or "").strip().upper()
        if title and rank in {"A", "B", "C"}:
            items.append({"abbr": title, "full_name": desc or title, "type": str(row.get("type") or "conference"), "field": str(row.get("sub") or row.get("field") or "Computer Science"), "level": rank, "aliases": sorted({title, desc} - {""})})
    return items


def update_ccf_file(path: Path, source_url: str | None = None) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    source_url = source_url or "https://raw.githubusercontent.com/ccfddl/ccf-deadlines/master/conference/AI.yml"
    try:
        response = requests.get(source_url, timeout=30)
        response.raise_for_status()
        items = _normalize_ccf_deadlines(yaml.safe_load(response.text))
        if not items:
            raise ValueError("CCF source did not contain usable items")
        payload = {"version": "ccf-deadlines", "source_url": source_url, "generated_at": datetime.now(timezone.utc).isoformat(), "items": items}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:
        cached = _load_cached(path)
        cached["warning"] = f"Using cached CCF data: {exc}"
        return cached
