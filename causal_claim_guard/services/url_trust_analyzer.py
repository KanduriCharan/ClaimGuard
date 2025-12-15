# services/url_trust_analyzer.py

import re
import socket
from dataclasses import dataclass
from typing import Optional, Dict, Any

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


@dataclass
class UrlAnalysis:
    host: str
    tld: str
    scheme: str
    type_inferred: str  # "peer-reviewed" | "whitepaper" | "news" | "blog" | "unknown"
    year_inferred: Optional[int]
    content_ok: bool
    content_length: int
    details: str


ACADEMIC_TLDS = {".edu", ".ac.uk", ".ac.in", ".ac", ".edu.au", ".edu.in"}
GOV_TLDS = {".gov", ".gov.uk", ".gov.in", ".gov.au"}
NEWS_HINTS = ["news", "reuters", "bbc", "nytimes", "bloomberg", "guardian"]
BLOG_HINTS = ["blog", "medium.com", "substack.com", "wordpress", "blogspot"]


def _extract_year_from_text(text: str) -> Optional[int]:
    """
    Very simple year extractor: look for 20xx in the text.
    Prefer years between 2000 and 2035.
    """
    candidates = re.findall(r"(20[0-3][0-9])", text)
    years = [int(y) for y in candidates if 2000 <= int(y) <= 2035]
    return min(years) if years else None


def _infer_type_from_host_and_path(host: str, path: str, text: str) -> str:
    host_lower = host.lower()
    path_lower = path.lower()
    combined = host_lower + " " + path_lower

    # Academic journals / preprints (very rough)
    if "pubmed" in combined or "ncbi.nlm.nih.gov" in combined or "doi.org" in combined:
        return "peer-reviewed"
    if "arxiv.org" in combined:
        return "whitepaper"

    # Govt health / finance portals behave like whitepapers
    if any(tld in host_lower for tld in GOV_TLDS | ACADEMIC_TLDS):
        return "whitepaper"

    # News-ish domains
    if any(h in host_lower for h in NEWS_HINTS):
        return "news"

    # Blogs
    if any(h in combined for h in BLOG_HINTS):
        return "blog"

    # If the page title says "blog"
    if "blog" in text.lower():
        return "blog"

    return "unknown"


def analyze_url(url: str, timeout: float = 4.0) -> UrlAnalysis:
    """
    Fetch the URL (best effort) and infer:
      - type_inferred: source category
      - year_inferred: approximate publication year
      - content_ok: did we get non-trivial content?
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    tld = ""
    for suffix in list(ACADEMIC_TLDS | GOV_TLDS) + [".org", ".com", ".net", ".info", ".xyz"]:
        if host.endswith(suffix.replace("*", "")):
            tld = suffix
            break

    # Default if fetch fails
    fallback = UrlAnalysis(
        host=host,
        tld=tld,
        scheme=parsed.scheme or "http",
        type_inferred="unknown",
        year_inferred=None,
        content_ok=False,
        content_length=0,
        details="URL present but could not fetch or parse."
    )

    if not host:
        return fallback

    try:
        # quick DNS check (avoid obvious garbage)
        socket.gethostbyname(host)
    except Exception:
        return fallback

    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "CausalClaimGuard/1.0"})
    except Exception:
        return fallback

    if not (200 <= resp.status_code < 300):
        return fallback

    content = resp.text or ""
    content_length = len(content)

    if content_length < 500:
        # too little to reason about
        return UrlAnalysis(
            host=host,
            tld=tld,
            scheme=parsed.scheme or "http",
            type_inferred="unknown",
            year_inferred=None,
            content_ok=False,
            content_length=content_length,
            details="Fetched but content too short to analyze."
        )

    # parse HTML
    try:
        soup = BeautifulSoup(content, "html.parser")
        title_text = (soup.title.string or "") if soup.title else ""
        meta_text_parts = []

        for m in soup.find_all("meta"):
            if m.get("content"):
                meta_text_parts.append(m.get("content"))

        meta_text = " ".join(meta_text_parts)[:5000]
        text_for_year = " ".join([title_text, meta_text])[:8000]

        year = _extract_year_from_text(text_for_year) or _extract_year_from_text(content[:20000])
        inferred_type = _infer_type_from_host_and_path(host, parsed.path, title_text + " " + meta_text)

        detail_bits = []
        if inferred_type != "unknown":
            detail_bits.append(f"type: {inferred_type}")
        if year:
            detail_bits.append(f"year≈{year}")
        if tld:
            detail_bits.append(f"tld={tld}")
        if not detail_bits:
            detail_bits.append("no strong signals")

        return UrlAnalysis(
            host=host,
            tld=tld,
            scheme=parsed.scheme or "http",
            type_inferred=inferred_type,
            year_inferred=year,
            content_ok=True,
            content_length=content_length,
            details="; ".join(detail_bits)
        )
    except Exception:
        return UrlAnalysis(
            host=host,
            tld=tld,
            scheme=parsed.scheme or "http",
            type_inferred="unknown",
            year_inferred=None,
            content_ok=True,
            content_length=content_length,
            details="Fetched but HTML parsing failed."
        )
