# services/explanation_service.py
from typing import Any, List


class ExplanationService:
    """
    Builds a short, human-readable explanation of:
      - what rung the claim is on (L1/L2/L3)
      - how we modeled it as an SCM (X, Y, Z)
      - whether the effect is identifiable and with what estimand
      - how strong the evidence is (T(m, c))
    """

    def _get(self, obj: Any, key: str, default=None):
        """Helper that works for both dicts and objects."""
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def build_explanation(
        self,
        text_claim: str,
        domain: str,
        rung: str,
        template: Any,
        estimand: Any,
        aggregated_trust: Any,
    ) -> str:
        # 1) Rung explanation
        if rung == "L1":
            rung_text = (
                "This is treated as an association-level (L1) claim: "
                "it describes patterns or correlations without explicit causal or counterfactual language."
            )
        elif rung == "L2":
            rung_text = (
                "This is treated as an intervention-level (L2) claim: "
                "it uses causal language (e.g., 'affects', 'reduces', 'causes') "
                "suggesting that changing the exposure would change the outcome."
            )
        else:  # L3 or unknown
            rung_text = (
                "This is treated as a counterfactual-level (L3) claim: "
                "it talks about what would have happened under a different hypothetical scenario."
            )

        # 2) SCM explanation (support X/x, Y/y, Z/z naming)
        X = self._get(template, "X", None) or self._get(template, "x", "an exposure")
        Y = self._get(template, "Y", None) or self._get(template, "y", "an outcome")
        Z = self._get(template, "Z", None) or self._get(template, "z", [])

        if Z:
            z_list = ", ".join(Z)
            scm_text = (
                f"In the {domain} domain, the system models this claim with '{X}' as the exposure (X) "
                f"and '{Y}' as the outcome (Y). It treats [{z_list}] as confounders Z that affect both X and Y. "
                "The SCM therefore includes edges Z → X, Z → Y, and X → Y."
            )
        else:
            scm_text = (
                f"In the {domain} domain, the system models this claim with '{X}' as the exposure (X) "
                f"and '{Y}' as the outcome (Y), but it does not currently include any confounders Z."
            )

        # 3) Estimand explanation (support Identifiable/identifiable etc.)
        identifiable = bool(
            self._get(estimand, "Identifiable", self._get(estimand, "identifiable", False))
        )
        expr = self._get(estimand, "Expression", self._get(estimand, "expression", ""))
        reason = self._get(estimand, "Reason", self._get(estimand, "reason", ""))

        if identifiable and expr:
            est_text = (
                "Under these assumptions, the causal effect P(Y | do(X)) is considered identifiable. "
                f"A valid estimand is: {expr}. "
                f"Reason: {reason}"
            )
        else:
            est_text = (
                "Given the available variables, the system cannot express P(Y | do(X)) using only observational quantities. "
                f"Reason: {reason or 'identifiability conditions are not met.'}"
            )

        # 4) Trust explanation – handle dict OR object, including details
        if isinstance(aggregated_trust, dict):
            m = aggregated_trust.get("m", 0.0)
            c = aggregated_trust.get("c", 0.0)
            details = aggregated_trust.get("Details", "") or aggregated_trust.get("details", "")
        else:
            m = getattr(aggregated_trust, "m", 0.0)
            c = getattr(aggregated_trust, "c", 0.0)
            details = getattr(aggregated_trust, "details", "")

        # Special case for "no sources"
        if m == 0.0 and c == 0.0 and details and "no sources" in details.lower():
            trust_text = (
                "No external evidence sources were provided, so the tool does not assign any trust score to this claim "
                "(trust T(m, c) defaults to (0, 0), representing complete uncertainty about the reliability of the evidence)."
            )
        else:
            trust_text = (
                f"Based on the provided sources, the aggregated trust in the evidence supporting this claim is "
                f"T(m, c) = ({m:.2f}, {c:.2f}), where m reflects overall trustworthiness and c reflects confidence in that assessment."
            )

        # 5) Combine
        explanation = (
            f"Claim: \"{text_claim}\"\n\n"
            f"{rung_text}\n\n"
            f"{scm_text}\n\n"
            f"{est_text}\n\n"
            f"{trust_text}"
        )

        return explanation
