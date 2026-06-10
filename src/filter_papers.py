from __future__ import annotations

from typing import Any

CCF_BONUS = {"A": 3, "B": 2, "C": 1}


def _keywords(values: list[str]) -> list[str]:
    return [value.strip().lower() for value in values if value and value.strip()]


def score_paper(paper: dict[str, Any], profile: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    title = str(paper.get("title") or "").lower()
    abstract = str(paper.get("abstract") or "").lower()
    categories = set(paper.get("categories") or [])
    include = _keywords(profile.get("include_keywords") or [])
    exclude = _keywords(profile.get("exclude_keywords") or [])
    targets = set(profile.get("arxiv_categories") or [])
    allowed_ccf = set(profile.get("ccf_levels") or [])
    if any(word in title or word in abstract for word in exclude):
        return False, paper
    score = 0
    matched: list[str] = []
    for keyword in include:
        hit = False
        if keyword in title:
            score += 3
            hit = True
        if keyword in abstract:
            score += 2
            hit = True
        if hit:
            matched.append(keyword)
    if targets and categories.intersection(targets):
        score += 1
    ccf_level = paper.get("ccf_level")
    if ccf_level in CCF_BONUS:
        score += CCF_BONUS[ccf_level]
    if allowed_ccf and ccf_level and ccf_level not in allowed_ccf:
        return False, paper
    paper["score"] = score
    paper["matched_keywords"] = matched
    return score >= int(profile.get("score_threshold", 3)), paper


def filter_papers(papers: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for paper in papers:
        ok, scored = score_paper(paper, profile)
        if ok:
            kept.append(scored)
    return kept
