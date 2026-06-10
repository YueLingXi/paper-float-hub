from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GROUPS = ["CCF-A", "CCF-B", "CCF-C", "arXiv", "unmatched"]


def deduplicate(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for paper in papers:
        pid = str(paper.get("id") or paper.get("url") or paper.get("title"))
        current = by_id.get(pid)
        if current is None or int(paper.get("score") or 0) > int(current.get("score") or 0):
            by_id[pid] = paper
    return sorted(by_id.values(), key=lambda p: (int(p.get("score") or 0), p.get("publish_date") or ""), reverse=True)


def _group_name(paper: dict[str, Any]) -> str:
    level = paper.get("ccf_level")
    if level in {"A", "B", "C"}:
        return f"CCF-{level}"
    return "arXiv" if paper.get("source") == "arxiv" else "unmatched"


def write_outputs(public_dir: Path, papers: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    public_dir.mkdir(parents=True, exist_ok=True)
    (public_dir / "papers").mkdir(parents=True, exist_ok=True)
    groups = {name: [] for name in GROUPS}
    for paper in papers:
        groups.setdefault(_group_name(paper), []).append(paper["id"])
    payload = {"generated_at": now.isoformat().replace("+00:00", "Z"), "date": now.date().isoformat(), "total": len(papers), "groups": groups, "papers": papers}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (public_dir / "latest.json").write_text(text, encoding="utf-8")
    (public_dir / "papers" / f"{payload['date']}.json").write_text(text, encoding="utf-8")
    return payload
