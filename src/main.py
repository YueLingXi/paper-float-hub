from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from build_output import deduplicate, write_outputs
from download_ccf import update_ccf_file
from fetch_arxiv import fetch_recent_arxiv
from filter_papers import filter_papers
from match_ccf import attach_ccf_level


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_profile(config: dict[str, Any]) -> dict[str, Any]:
    for profile in config.get("profiles") or []:
        if profile.get("enabled"):
            return profile
    raise ValueError("No enabled profile found in config/profiles.yml")


def run() -> None:
    root = Path(__file__).resolve().parent.parent
    config = load_config(root / "config" / "profiles.yml")
    profile = load_profile(config)
    fetch_cfg = config.get("fetch") or {}
    ccf_cfg = config.get("ccf") or {}
    print("[1/5] Updating CCF cache")
    ccf_data = update_ccf_file(root / "rank" / "ccf.json", ccf_cfg.get("source_url"))
    print("[2/5] Fetching arXiv papers")
    papers = fetch_recent_arxiv(
        days_back=int(fetch_cfg.get("days_back", 2)),
        arxiv_set=str(fetch_cfg.get("arxiv_set", "cs")),
        categories=profile.get("arxiv_categories") or None,
    )
    print(f"Fetched {len(papers)} papers")
    print("[3/5] Matching CCF metadata")
    papers = attach_ccf_level(papers, ccf_data.get("items") or [])
    print("[4/5] Filtering and scoring")
    papers = deduplicate(filter_papers(papers, profile))
    print(f"Kept {len(papers)} papers")
    print("[5/5] Writing public output")
    payload = write_outputs(root / "public", papers)
    print(json.dumps({"date": payload["date"], "total": payload["total"]}, ensure_ascii=False))


if __name__ == "__main__":
    run()
