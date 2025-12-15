# services/trust_engine.py

from typing import List, Dict, Any, Tuple, Optional

from .url_trust_analyzer import analyze_url, UrlAnalysis


def _score_source(
    source_type: Optional[str],
    year: Optional[int],
    sample_size: Optional[int],
    url_info: Optional[UrlAnalysis]
) -> Tuple[float, float, str]:
    """
    Compute (m, c, details) for a single source using:
      - declared type/year/sample from user
      - inferred type/year/tld/content from URL
    """

    # ---------- 1. Decide effective type ----------

    declared_type = (source_type or "").lower().strip()
    inferred_type = (url_info.type_inferred if url_info else "unknown") or "unknown"

    # If user didn't provide type, trust URL inference
    if not declared_type:
        effective_type = inferred_type
        type_origin = "inferred from URL"
    else:
        # If they say "peer-reviewed" but URL looks like a random blog, we downgrade a bit
        if declared_type == "peer-reviewed" and inferred_type == "blog":
            effective_type = "whitepaper"
            type_origin = "user=peer-reviewed, URL looks like blog → downgraded to whitepaper"
        else:
            effective_type = declared_type
            type_origin = "user-provided"

    # map effective type to base trust
    type_weights = {
        "peer-reviewed": 0.9,
        "whitepaper": 0.75,
        "news": 0.6,
        "blog": 0.4,
        "unknown": 0.35,
    }
    type_score = type_weights.get(effective_type, 0.35)

    # ---------- 2. Year score (manual or inferred) ----------

    y = year or (url_info.year_inferred if url_info else None)
    if y is None:
        year_score = 0.5  # neutral
        year_detail = "year: unknown"
    else:
        if y >= 2020:
            year_score = 0.95
        elif y >= 2010:
            year_score = 0.7
        else:
            year_score = 0.4
        year_detail = f"year≈{y}"

    # ---------- 3. Sample size score ----------

    if sample_size is None or sample_size <= 0:
        sample_score = 0.5
        sample_detail = "n: unknown"
    else:
        if sample_size >= 1000:
            sample_score = 0.95
        elif sample_size >= 200:
            sample_score = 0.75
        elif sample_size >= 50:
            sample_score = 0.6
        else:
            sample_score = 0.4
        sample_detail = f"n={sample_size}"

    # ---------- 4. URL credibility tweaks ----------

    url_detail = ""
    domain_bonus = 0.0
    confidence_bonus = 0.0

    if url_info:
        url_detail = url_info.details

        # academic / gov TLDS → boost trust & confidence
        if url_info.tld in (".edu", ".ac.uk", ".ac.in", ".gov", ".gov.uk", ".gov.in"):
            domain_bonus += 0.07
            confidence_bonus += 0.1

        # content long enough and parsed → more confidence
        if url_info.content_ok and url_info.content_length > 4000:
            confidence_bonus += 0.1

    # ---------- 5. Aggregate m ----------

    m_raw = (type_score + year_score + sample_score) / 3.0 + domain_bonus
    m = max(0.0, min(1.0, m_raw))

    # ---------- 6. Confidence c ----------

    c_base = 0.3
    # high type certainty
    if effective_type in ("peer-reviewed", "whitepaper", "news"):
        c_base += 0.2
    # year known
    if y is not None:
        c_base += 0.2
    # sample size known and decent
    if sample_size and sample_size >= 50:
        c_base += 0.1

    c = max(0.0, min(1.0, c_base + confidence_bonus))

    details = f"type={effective_type} ({type_origin}); {year_detail}; {sample_detail}"
    if url_detail:
        details += f"; url: {url_detail}"

    return m, c, details


def evaluate_source_trust(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate trust for a single source dict from the API payload.

    Expected source fields (all optional):
      - Title
      - Url
      - Type
      - SampleSize
      - Year
      - PeerReviewed
    """
    url = source.get("Url")
    url_info = analyze_url(url) if url else None

    source_type = source.get("Type")
    # if user explicitly sets PeerReviewed true, treat as peer-reviewed
    if source.get("PeerReviewed"):
        source_type = "peer-reviewed"

    year = source.get("Year")
    sample_size = source.get("SampleSize")

    m, c, details = _score_source(source_type, year, sample_size, url_info)

    return {
        "m": m,
        "c": c,
        "Source": url or source.get("Title", "unknown"),
        "Details": details,
    }


def aggregate_trust(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate trust over a list of per-source trust dicts.
    """
    if not sources:
        return {
            "m": 0.0,
            "c": 0.0,
            "Source": "aggregate",
            "Details": "no sources provided",
        }

    ms = [s["m"] for s in sources]
    cs = [s["c"] for s in sources]
    m_agg = sum(ms) / len(ms)
    c_agg = sum(cs) / len(cs)

    return {
        "m": m_agg,
        "c": c_agg,
        "Source": "aggregate",
        "Details": f"aggregated over {len(sources)} sources",
    }


def compute_trust_for_sources(source_payloads: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    per_source = [evaluate_source_trust(s) for s in source_payloads]
    return per_source, aggregate_trust(per_source)
