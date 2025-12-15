from flask import Flask, request, jsonify
from flask_cors import CORS

from services.explanation_service import ExplanationService
from services.trust_engine import compute_trust_for_sources   # ⬅️ NEW: URL-aware trust
# ⬆️ you can delete the old TrustService import

from models import (
    AnalyzeRequest,
    SourceRef,
    AnalyzeResponse,
)
from services.claim_classifier import ClaimClassifier
from services.scm_builder import ScmBuilder
from services.estimand_service import EstimandService
# from services.trust_service import TrustService  # ⬅️ REMOVE THIS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

claim_classifier = ClaimClassifier()
scm_builder = ScmBuilder()
estimand_service = EstimandService()
# trust_service = TrustService()                  # ⬅️ REMOVE THIS
explanation_service = ExplanationService()


@app.route("/", methods=["GET"])
def health():
    return jsonify(
        {
            "ok": True,
            "service": "CausalClaim Guard Backend (Flask)",
            "version": "0.1.0",
        }
    )


@app.route("/analyze_claim", methods=["POST"])
def analyze_claim():
    data = request.get_json(force=True) or {}

    text_claim = data.get("TextClaim") or data.get("text_claim") or ""
    domain = data.get("Domain") or data.get("domain") or "health"
    raw_sources = data.get("Sources") or data.get("sources") or []

    # Keep this: we still build SourceRef objects for the request model
    sources = []
    for s in raw_sources:
        sources.append(
            SourceRef(
                title=s.get("Title") or s.get("title"),
                url=s.get("Url") or s.get("url"),
                type=s.get("Type") or s.get("type"),
                sample_size=s.get("SampleSize") or s.get("sample_size"),
                year=s.get("Year") or s.get("year"),
                peer_reviewed=s.get("PeerReviewed") or s.get("peer_reviewed"),
            )
        )

    req_obj = AnalyzeRequest(
        text_claim=text_claim,
        domain=domain.lower(),
        sources=sources,
    )

    # 1) classify claim
    rung = claim_classifier.classify(req_obj.text_claim)

    # 2) build SCM template
    template = scm_builder.build_template(req_obj.text_claim, req_obj.domain)

    # 3) compute estimand
    estimand = estimand_service.compute(template)

    # 4) NEW: compute trust with URL-aware engine
    #    raw_sources is the original list of dicts coming from JSON.
    source_trust, aggregated_trust = compute_trust_for_sources(raw_sources)

    # 5) explanation (unchanged, but now uses the new aggregated_trust dict)
    explanation = explanation_service.build_explanation(
        text_claim=req_obj.text_claim,
        domain=req_obj.domain,
        rung=rung,
        template=template,
        estimand=estimand,
        aggregated_trust=aggregated_trust,
    )

    # 6) response object
    resp = AnalyzeResponse(
        text_claim=req_obj.text_claim,
        domain=req_obj.domain,
        rung=rung,
        template=template,
        estimand=estimand,
        source_trust=source_trust,
        aggregated_trust=aggregated_trust,
        explanation=explanation,
    )

    return jsonify(resp.to_dict())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
