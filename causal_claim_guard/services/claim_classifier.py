# services/claim_classifier.py
import re


class ClaimClassifier:
    """
    Classifies a natural language claim into Pearl's Causal Ladder:
      - L1: Association (correlation / observation only)
      - L2: Intervention (causal / effect language)
      - L3: Counterfactual (what would have happened if...)
    We use simple regex markers tuned for your project domains.
    """

    # RUNG 3 (L3) — counterfactual language
    L3_MARKERS = [
        r"\bwhat if\b",               # "what if he had..."
        r"\bhadn['’]t\b",             # "hadn't"
        r"\bhad\b.*\bnot\b",          # "had not"
        r"\bif\b.*\bhad\b",           # "if he had", "if she had"
        r"\bwould have\b",            # "would have slept"
        r"\bcould have\b",            # "could have avoided"
        r"\bshould have\b",           # "should have done"
        r"\bmight have\b",            # "might have changed"
        r"\bcounterfactual\b",
    ]

    # RUNG 2 (L2) — causal / intervention language
    L2_MARKERS = [
        r"\bcause(s|d)?\b",           # cause, causes, caused
        r"\bcausal\b",
        r"\baffect(s|ed|ing)?\b",     # affect, affects, affected, affecting
        r"\bimpact(s|ed|ing)?\b",     # impact, impacts, impacted, impacting
        r"\bleads? to\b",             # lead to, leads to
        r"\bresults? in\b",           # result in, results in
        r"\breduce(s|d)?\b",          # reduce, reduces, reduced
        r"\bincrease(s|d)?\b",        # increase, increases, increased
        r"\bimprove(s|d)?\b",         # improve, improves, improved
        r"\bworsen(s|ed|ing)?\b",     # worsen, worsened, worsening
        r"\bprevent(s|ed|ing)?\b",    # prevent, prevents, prevented
        r"\bprotect(s|ed|ing)?\b",    # protect, protects, protected
    ]

    def classify(self, text: str) -> str:
        """
        Return:
          - "L3" if counterfactual language is detected
          - "L2" if causal / intervention language is detected
          - "L1" otherwise (association-level)
        """
        t = text.lower()

        # Check for L3 markers first (highest rung)
        for pat in self.L3_MARKERS:
            if re.search(pat, t):
                return "L3"

        # Then check for L2 markers
        for pat in self.L2_MARKERS:
            if re.search(pat, t):
                return "L2"

        # Default: L1 (association)
        return "L1"
