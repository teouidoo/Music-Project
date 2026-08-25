from decimal import Decimal

from rightsflow.report import render_waterfall
from rightsflow.waterfall import RightsHolder, Scenario, run_waterfall


def test_report_discloses_undistributed_pool():
    scenario = Scenario(
        name="one-sided",
        description="test",
        platform_share=Decimal("0.55"),
        recorded_share=Decimal("0.5"),
        publishing_share=Decimal("0.5"),
        rightsholders=(RightsHolder("A", "recorded", Decimal("1")),),
    )
    report = render_waterfall(run_waterfall(scenario, Decimal("1000")))
    assert "UNDISTRIBUTED (no publishing holders)" in report
    assert "TOTAL PAID + UNDISTRIBUTED = POOL" in report
