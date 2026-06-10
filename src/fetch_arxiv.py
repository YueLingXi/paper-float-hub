from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any
from xml.etree import ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SEARCH_ENDPOINT = "https://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}

_RETRY_DELAYS = [10, 30, 60]
_PAGE_SIZE = 500


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _get(params: dict[str, Any]) -> ET.Element:
    last_exc: Exception | None = None
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            print(f"  arXiv request failed, retrying in {delay}s (attempt {attempt + 1}/{len(_RETRY_DELAYS) + 1})...")
            time.sleep(delay)
        try:
            resp = _session().get(
                SEARCH_ENDPOINT,
                params=params,
                timeout=90,
                headers={"User-Agent": "paper-float-hub/0.1"},
            )
            resp.raise_for_status()
            return ET.fromstring(resp.text)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_exc = exc
    raise RuntimeError(f"arXiv request failed after {len(_RETRY_DELAYS) + 1} attempts") from last_exc


def _parse_entry(entry: ET.Element) -> dict[str, Any] | None:
    id_url = _clean(entry.findtext("atom:id", namespaces=NS))
    if not id_url:
        return None
    # URL format: https://arxiv.org/abs/2401.12345v1 — strip version suffix
    arxiv_id = id_url.rstrip("/").rsplit("/", 1)[-1]
    if "v" in arxiv_id:
        arxiv_id = arxiv_id[: arxiv_id.rfind("v")]

    categories = [tag.get("term", "") for tag in entry.findall("atom:category", NS) if tag.get("term")]
    publish_date = _clean(entry.findtext("atom:published", namespaces=NS))[:10]
    authors = [
        _clean(a.findtext("atom:name", namespaces=NS))
        for a in entry.findall("atom:author", NS)
        if _clean(a.findtext("atom:name", namespaces=NS))
    ]
    return {
        "id": f"arxiv:{arxiv_id}",
        "title": _clean(entry.findtext("atom:title", namespaces=NS)),
        "abstract": _clean(entry.findtext("atom:summary", namespaces=NS)),
        "authors": authors,
        "source": "arxiv",
        "publish_date": publish_date,
        "venue": None,
        "ccf_level": None,
        "arxiv_category": categories[0] if categories else None,
        "categories": categories,
        "matched_keywords": [],
        "score": 0,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
    }


def fetch_recent_arxiv(
    days_back: int = 2,
    arxiv_set: str = "cs",
    categories: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch recent arXiv papers via the Search API (much faster than OAI-PMH).

    When `categories` is provided (e.g. ["cs.AI", "cs.CL"]) only those
    sub-categories are queried, keeping the response small and reliable.
    Falls back to all papers in `arxiv_set` (e.g. "cs.*") if not given.
    """
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days_back)

    if categories:
        cat_query = " OR ".join(f"cat:{c}" for c in categories)
    else:
        cat_query = f"cat:{arxiv_set}.*"

    # arXiv Search API date format: YYYYMMDDHHMMSS
    date_from = since.strftime("%Y%m%d000000")
    date_until = now.strftime("%Y%m%d235959")
    query = f"({cat_query}) AND submittedDate:[{date_from} TO {date_until}]"

    papers: list[dict[str, Any]] = []
    start = 0

    while True:
        params: dict[str, Any] = {
            "search_query": query,
            "start": start,
            "max_results": _PAGE_SIZE,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        root = _get(params)

        entries = root.findall("atom:entry", NS)
        if not entries:
            break

        for entry in entries:
            paper = _parse_entry(entry)
            if paper:
                papers.append(paper)

        total_str = _clean(root.findtext("opensearch:totalResults", namespaces=NS))
        total = int(total_str) if total_str.isdigit() else 0
        start += len(entries)

        if start >= total or len(entries) < _PAGE_SIZE:
            break

        # arXiv API guidelines ask for a small delay between paginated requests
        time.sleep(3)

    return papers
