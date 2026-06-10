from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any
from xml.etree import ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

OAI_ENDPOINT = "https://export.arxiv.org/oai2"
NS = {"oai": "http://www.openarchives.org/OAI/2.0/", "arxiv": "http://arxiv.org/OAI/arXiv/"}

_RETRY_DELAYS = [10, 30, 60]


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def _authors(parent: ET.Element | None) -> list[str]:
    if parent is None:
        return []
    names: list[str] = []
    for author in parent.findall("arxiv:author", NS):
        keyname = _clean(author.findtext("arxiv:keyname", namespaces=NS))
        forenames = _clean(author.findtext("arxiv:forenames", namespaces=NS))
        name = " ".join([forenames, keyname]).strip() or keyname
        if name:
            names.append(name)
    return names


def _record(node: ET.Element) -> dict[str, Any] | None:
    header = node.find("oai:header", NS)
    metadata = node.find("oai:metadata", NS)
    meta = metadata.find("arxiv:arXiv", NS) if metadata is not None else None
    if header is None or meta is None:
        return None
    arxiv_id = _clean(meta.findtext("arxiv:id", namespaces=NS))
    if not arxiv_id:
        return None
    categories = _clean(meta.findtext("arxiv:categories", namespaces=NS)).split()
    datestamp = _clean(header.findtext("oai:datestamp", namespaces=NS))
    return {"id": f"arxiv:{arxiv_id}", "title": _clean(meta.findtext("arxiv:title", namespaces=NS)), "abstract": _clean(meta.findtext("arxiv:abstract", namespaces=NS)), "authors": _authors(meta.find("arxiv:authors", NS)), "source": "arxiv", "publish_date": datestamp[:10], "venue": None, "ccf_level": None, "arxiv_category": categories[0] if categories else None, "categories": categories, "matched_keywords": [], "score": 0, "url": f"https://arxiv.org/abs/{arxiv_id}", "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf"}


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _request(params: dict[str, str]) -> ET.Element:
    last_exc: Exception | None = None
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            print(f"  arXiv request timed out, retrying in {delay}s (attempt {attempt + 1}/{len(_RETRY_DELAYS) + 1})...")
            time.sleep(delay)
        try:
            response = _session().get(OAI_ENDPOINT, params=params, timeout=90, headers={"User-Agent": "paper-float-hub/0.1"})
            response.raise_for_status()
            return ET.fromstring(response.text)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_exc = exc
    raise RuntimeError(f"arXiv OAI request failed after {len(_RETRY_DELAYS) + 1} attempts") from last_exc


def fetch_recent_arxiv(days_back: int = 2, arxiv_set: str = "cs") -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    params = {"verb": "ListRecords", "from": (now - timedelta(days=days_back)).strftime("%Y-%m-%d"), "until": now.strftime("%Y-%m-%d"), "metadataPrefix": "arXiv", "set": arxiv_set}
    papers: list[dict[str, Any]] = []
    while True:
        root = _request(params)
        papers.extend(p for p in (_record(node) for node in root.findall(".//oai:record", NS)) if p)
        token_node = root.find(".//oai:resumptionToken", NS)
        token = _clean(token_node.text if token_node is not None else "")
        if not token:
            return papers
        params = {"verb": "ListRecords", "resumptionToken": token}
