# services/estimand_service.py
from models import ScmTemplate, EstimandResult


class EstimandService:
    def compute(self, tpl: ScmTemplate) -> EstimandResult:
        if not tpl.z:
            return EstimandResult(
                identifiable=False,
                expression="",
                reason="Back-door not satisfied with available variables; require experiment or instrument.",
            )

        z_list = ", ".join(tpl.z)
        expr = f"Sum_{{{z_list}}} P({tpl.y}|{tpl.x}, {z_list}) * P({z_list})"

        return EstimandResult(
            identifiable=True,
            expression=expr,
            reason="Back-door criterion satisfied using Z.",
        )
