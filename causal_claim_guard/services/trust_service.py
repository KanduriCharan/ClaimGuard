# services/trust_service.py
import math
from typing import List
from models import SourceRef, TrustTuple


class TrustService:
    def score_sources(self, sources: List[SourceRef]) -> List[TrustTuple]:
        result: List[TrustTuple] = []

        for s in sources:
            base_m = 0.5
            if s.type:
                t = s.type.lower()
                if t == "peer-reviewed":
                    base_m = 0.85
                elif t == "whitepaper":
                    base_m = 0.70
                elif t == "news":
                    base_m = 0.60
                elif t == "blog":
                    base_m = 0.45

            if s.sample_size and s.sample_size > 1000:
                base_m += 0.05
            if s.peer_reviewed:
                base_m += 0.05

            base_m = min(max(base_m, 0.0), 1.0)

            c = 0.5
            if s.year is not None:
                from datetime import datetime

                current_year = datetime.now().year
                if current_year - s.year <= 2:
                    c += 0.2
            if s.title and s.url:
                c += 0.1

            c = min(max(c, 0.0), 1.0)

            src_label = s.url or s.title or None

            result.append(
                TrustTuple(
                    m=base_m,
                    c=c,
                    source=src_label,
                    details=s.type,
                )
            )

        return result

    def aggregate(self, tuples: List[TrustTuple]) -> TrustTuple:
        if not tuples:
            return TrustTuple(
                m=0.0,
                c=0.0,
                source="aggregate",
                details="no sources provided",
            )

        wsum = sum(t.c for t in tuples)
        if wsum > 0:
            m = sum(t.m * t.c for t in tuples) / wsum
        else:
            m = sum(t.m for t in tuples) / len(tuples)

        variance = sum((t.m - m) ** 2 for t in tuples) / len(tuples)
        agreement = 1.0 - math.sqrt(variance)
        agreement = min(max(agreement, 0.0), 1.0)

        n = len(tuples)
        c = 0.4 + 0.2 * math.log10(n + 1) + 0.4 * agreement
        c = min(max(c, 0.0), 1.0)

        return TrustTuple(
            m=m,
            c=c,
            source="aggregate",
            details=f"n={n}, agreement≈{agreement:.2f}",
        )
