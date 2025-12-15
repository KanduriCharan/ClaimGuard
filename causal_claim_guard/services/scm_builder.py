# services/scm_builder.py
import re
from typing import Tuple, Optional

from models import ScmTemplate
from domain_vocab import DOMAIN_DICTIONARY, DomainConfig, ExposureConfig


class ScmBuilder:
    """
    Builds an SCM template (X, Y, Z, edges) for a given claim and domain.

    NEW (Step 2):
      - First, try to extract candidate X/Y phrases from the claim text using
        simple causal patterns like
          "[NP1] causes [NP2]"
          "[NP1] increases [NP2]"
          "[NP1] leads to [NP2]"
      - Then, map those phrases to the closest exposure/outcome terms from the
        domain vocabulary using token overlap / substring matching.
      - If that fails, fall back to the original behavior:
          * pick exposure whose name appears in the claim (else first)
          * pick outcome whose name appears in the claim (else first)
    """

    # simple causal patterns for L2-style claims
    VERB_PATTERNS = [
        r"(.+?)\s+(causes?|affects?|impacts?|increases?|reduces?|improves?|worsens?)\s+(.+)",
        r"(.+?)\s+leads?\s+to\s+(.+)",
        r"(.+?)\s+results?\s+in\s+(.+)",
    ]

    def _get_domain_config(self, domain: str) -> DomainConfig:
        return DOMAIN_DICTIONARY.get(domain, DOMAIN_DICTIONARY["health"])

    # ---------- X/Y extraction from raw text ----------

    def _extract_xy_candidates(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Try to extract (candidate_X_phrase, candidate_Y_phrase) from the claim text
        using simple causal patterns. Returns (None, None) if no pattern matches.
        """
        t = (text or "").strip()

        # Work in lowercase for matching, but keep original text for slicing
        lower = t.lower()

        for pat in self.VERB_PATTERNS:
            m = re.match(pat, lower)
            if m:
                left = m.group(1).strip()
                right = m.group(3).strip() if m.lastindex >= 3 else m.group(2).strip()

                # Very rough cleanup: remove trailing punctuation
                left = re.sub(r"[.,!?;:]+$", "", left)
                right = re.sub(r"[.,!?;:]+$", "", right)

                if left and right:
                    return left, right

        return None, None

    def _best_match(self, phrase: str, candidates: list[str]) -> Optional[str]:
        """
        Map a free-text phrase to the closest candidate string using:
          - substring bonus
          - token overlap
        Returns None if there is no overlap at all.
        """
        phrase = (phrase or "").lower()
        phrase_tokens = set(re.findall(r"\w+", phrase))

        best = None
        best_score = 0

        for cand in candidates:
            cand_lower = cand.lower()
            cand_tokens = set(re.findall(r"\w+", cand_lower))

            # strong bonus if one is substring of the other
            if cand_lower in phrase or phrase in cand_lower:
                score = len(cand_tokens) + 1
            else:
                score = len(phrase_tokens & cand_tokens)

            if score > best_score:
                best_score = score
                best = cand

        if best_score == 0:
            return None
        return best

    # ---------- Legacy fallback logic ----------

    def _fallback_exposure_and_outcome(
        self, text: str, domain_cfg: DomainConfig
    ) -> Tuple[ExposureConfig, str]:
        """
        Original behavior:
          - exposure = first whose name appears in claim (else first exposure)
          - outcome = first of that exposure whose name appears in claim (else first outcome)
        """
        t = text.lower()

        exposure = None
        for exp in domain_cfg.exposures:
            if exp.name.lower() in t:
                exposure = exp
                break
        if exposure is None:
            exposure = domain_cfg.exposures[0]

        outcome = None
        for y in exposure.outcomes:
            if y.lower() in t:
                outcome = y
                break
        if outcome is None:
            outcome = exposure.outcomes[0]

        return exposure, outcome

    # ---------- Combined logic ----------

    def _pick_exposure_and_outcome(
        self, text: str, domain_cfg: DomainConfig
    ) -> Tuple[ExposureConfig, str]:
        """
        1) Try pattern-based X/Y extraction + mapping to domain vocabulary.
        2) If that fails, fall back to the original simple matching logic.
        """
        # 1) Pattern-based extraction
        x_phrase, y_phrase = self._extract_xy_candidates(text)

        if x_phrase or y_phrase:
            # try to map X phrase to an exposure name
            exposure_names = [exp.name for exp in domain_cfg.exposures]
            exp_name = None
            if x_phrase:
                exp_name = self._best_match(x_phrase, exposure_names)

            # If mapping failed, try using full text or fallback
            exposure = None
            if exp_name is not None:
                for exp in domain_cfg.exposures:
                    if exp.name == exp_name:
                        exposure = exp
                        break

            if exposure is None:
                # we couldn't map nicely; fall back to legacy behavior
                return self._fallback_exposure_and_outcome(text, domain_cfg)

            # Map Y phrase to one of this exposure's outcomes
            outcome = None
            if y_phrase and exposure.outcomes:
                outcome = self._best_match(y_phrase, exposure.outcomes)

            if outcome is None:
                # as a fallback, reuse old outcome logic restricted to this exposure
                t = text.lower()
                for y in exposure.outcomes:
                    if y.lower() in t:
                        outcome = y
                        break
                if outcome is None:
                    outcome = exposure.outcomes[0]

            return exposure, outcome

        # 2) No pattern matched → fallback to simple behavior
        return self._fallback_exposure_and_outcome(text, domain_cfg)

    # ---------- Public API ----------

    def build_template(self, text: str, domain: str) -> ScmTemplate:
        domain_cfg = self._get_domain_config(domain)
        exposure_cfg, outcome = self._pick_exposure_and_outcome(text, domain_cfg)

        tpl = ScmTemplate()
        tpl.x = exposure_cfg.name
        tpl.y = outcome
        tpl.z = list(exposure_cfg.confounders)

        # edges: X -> Y, and for each confounder z: z -> X and z -> Y
        tpl.edges.append((tpl.x, tpl.y))
        for z in tpl.z:
            tpl.edges.append((z, tpl.x))
            tpl.edges.append((z, tpl.y))

        tpl.note = (
            "Auto-generated SCM template based on domain vocabulary and "
            "pattern-based extraction from the claim text. User can edit this at the UI level."
        )
        return tpl
