from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any


# ----------- Input models -----------

@dataclass
class SourceRef:
    title: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None    # "peer-reviewed", "news", "blog", etc.
    sample_size: Optional[int] = None
    year: Optional[int] = None
    peer_reviewed: Optional[bool] = None


@dataclass
class AnalyzeRequest:
    text_claim: str
    domain: str = "health"
    sources: List[SourceRef] = field(default_factory=list)


# ----------- SCM / estimand models -----------

@dataclass
class ScmTemplate:
    x: str = ""
    y: str = ""
    z: List[str] = field(default_factory=list)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    note: str = ""


@dataclass
class EstimandResult:
    identifiable: bool = False
    expression: str = ""
    reason: str = ""


# ----------- Trust models -----------

@dataclass
class TrustTuple:
    m: float = 0.0   # trustworthiness
    c: float = 0.0   # confidence
    source: Optional[str] = None
    details: Optional[str] = None


# ----------- Response model -----------

@dataclass
class AnalyzeResponse:
    text_claim: str
    domain: str
    rung: str  # "L1", "L2", "L3"
    template: ScmTemplate
    estimand: EstimandResult
    # NOTE: after introducing the new trust engine, these may be dicts OR TrustTuple
    source_trust: List[Any] = field(default_factory=list)
    aggregated_trust: Any = None
    explanation: str = ""  # natural language explanation

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert response to a JSON-serializable dict.
        Handles both TrustTuple objects and plain dicts for trust fields.
        """

        def trust_to_dict(t: Any) -> Dict[str, Any]:
            # Works for both dicts and TrustTuple-like objects
            if isinstance(t, dict):
                return {
                    "m": t.get("m", 0.0),
                    "c": t.get("c", 0.0),
                    "Source": t.get("Source") or t.get("source"),
                    "Details": t.get("Details") or t.get("details", ""),
                }
            else:
                return {
                    "m": getattr(t, "m", 0.0),
                    "c": getattr(t, "c", 0.0),
                    "Source": getattr(t, "source", None),
                    "Details": getattr(t, "details", "") or "",
                }

        # Template as dict
        template_dict = {
            "X": self.template.x,
            "Y": self.template.y,
            "Z": list(self.template.z),
            "Edges": list(self.template.edges),
            "Note": self.template.note,
        }

        # Estimand as dict
        estimand_dict = {
            "Identifiable": self.estimand.identifiable,
            "Expression": self.estimand.expression,
            "Reason": self.estimand.reason,
        }

        # Trust lists / aggregate
        source_trust_list = [trust_to_dict(t) for t in (self.source_trust or [])]
        aggregated_trust_dict = (
            trust_to_dict(self.aggregated_trust)
            if self.aggregated_trust is not None
            else trust_to_dict({})
        )

        return {
            "TextClaim": self.text_claim,
            "Domain": self.domain,
            "Rung": self.rung,
            "Template": template_dict,
            "Estimand": estimand_dict,
            "SourceTrust": source_trust_list,
            "AggregatedTrust": aggregated_trust_dict,
            "Explanation": self.explanation,
        }
