from decimal import Decimal

import pytest

from rightsflow.usage import UsageEvent, allocate_usage
from rightsflow.waterfall import RightsHolder, Scenario


def scenario():
    return Scenario(
        name="usage",
        description="test",
        platform_share=Decimal("0.55"),
        recorded_share=Decimal("0.5"),
        publishing_share=Decimal("0.5"),
        rightsholders=(
            RightsHolder("Label A", "recorded", Decimal("1"), id="label-a"),
            RightsHolder("Label B", "recorded", Decimal("1"), id="label-b"),
            RightsHolder("Publisher", "publishing", Decimal("1"), id="publisher"),
        ),
    )


def test_declared_usage_rollup_ties_per_track_to_cent():
    events = [
        UsageEvent("track-1", Decimal("10.01"), {"label-a": Decimal("3"), "label-b": Decimal("1"), "publisher": Decimal("1")}, "declared"),
        UsageEvent("track-2", Decimal("7.03"), {"label-a": Decimal("1"), "label-b": Decimal("2"), "publisher": Decimal("1")}, "declared"),
    ]
    result = allocate_usage(scenario(), events)
    result.assert_conservation()
    assert result.gross_revenue == Decimal("17.04")
    assert sum(result.payouts().values()) == result.total_paid


def test_usage_requires_source_and_known_holder():
    with pytest.raises(ValueError, match="attribution_source"):
        UsageEvent("track", Decimal("1"), {"label-a": Decimal("1")}, "api")
    event = UsageEvent("track", Decimal("1"), {"unknown": Decimal("1")}, "declared")
    with pytest.raises(ValueError, match="unknown"):
        allocate_usage(scenario(), [event])


def test_duplicate_event_id_is_rejected():
    event = UsageEvent("track", Decimal("1"), {"label-a": Decimal("1"), "label-b": Decimal("1"), "publisher": Decimal("1")}, "declared")
    with pytest.raises(ValueError, match="duplicate event_id"):
        allocate_usage(scenario(), [event, event])


def test_one_sided_event_reports_other_pool_as_undistributed():
    event = UsageEvent("track", Decimal("10"), {"label-a": Decimal("1")}, "declared")
    result = allocate_usage(scenario(), [event])
    assert result.undistributed > 0
    result.assert_conservation()


def test_repeated_track_is_allowed_with_unique_event_ids():
    weights = {"label-a": Decimal("1"), "publisher": Decimal("1")}
    events = [
        UsageEvent("track", Decimal("1"), weights, "declared", event_id="jan"),
        UsageEvent("track", Decimal("2"), weights, "declared", event_id="feb"),
    ]
    result = allocate_usage(scenario(), events, manifest_track_ids={"track"})
    assert result.gross_revenue == Decimal("3.00")


def test_manifest_linkage_is_optional_but_enforceable():
    event = UsageEvent("missing", Decimal("1"), {"label-a": Decimal("1")}, "declared")
    with pytest.raises(ValueError, match="not found in manifest"):
        allocate_usage(scenario(), [event], manifest_track_ids={"known"})
