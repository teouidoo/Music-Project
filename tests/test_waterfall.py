from decimal import Decimal

import pytest

from rightsflow.waterfall import RightsHolder, Scenario, run_waterfall


def scenario(platform="0.55", rec="0.5", pub="0.5", holders=None):
    holders = holders or [
        RightsHolder("Indie Label A", "recorded", Decimal("5")),
        RightsHolder("Indie Label B", "recorded", Decimal("3")),
        RightsHolder("Indie Label C", "recorded", Decimal("2")),
        RightsHolder("Publisher X", "publishing", Decimal("6")),
        RightsHolder("Publisher Y", "publishing", Decimal("4")),
    ]
    return Scenario(
        name="t", description="t",
        platform_share=Decimal(platform),
        recorded_share=Decimal(rec),
        publishing_share=Decimal(pub),
        rightsholders=tuple(holders),
    )


def test_known_values_run_to_the_cent():
    r = run_waterfall(scenario(), Decimal("1000000"))
    assert r.platform_retained == Decimal("550000.00")
    assert r.royalty_pool == Decimal("450000.00")
    assert r.recorded_pool == Decimal("225000.00")
    assert r.publishing_pool == Decimal("225000.00")
    assert r.payout("Indie Label A") == Decimal("112500.00")
    assert r.payout("Indie Label B") == Decimal("67500.00")
    assert r.payout("Indie Label C") == Decimal("45000.00")
    assert r.payout("Publisher X") == Decimal("135000.00")
    assert r.payout("Publisher Y") == Decimal("90000.00")


@pytest.mark.parametrize("revenue", ["1000000.01", "999999.99", "0.03", "123456.78", "1", "777777.77"])
def test_conservation_on_awkward_amounts(revenue):
    r = run_waterfall(scenario(), Decimal(revenue))
    r.assert_conservation()  # raises on any leak
    paid = sum(a.amount for a in r.allocations)
    assert paid == r.recorded_pool + r.publishing_pool


def test_largest_remainder_indivisible_cents():
    holders = [
        RightsHolder("A", "recorded", Decimal("1")),
        RightsHolder("B", "recorded", Decimal("1")),
        RightsHolder("C", "recorded", Decimal("1")),
    ]
    s = scenario(platform="0", rec="1", pub="0", holders=holders)
    r = run_waterfall(s, Decimal("100.00"))
    amounts = sorted((a.amount for a in r.allocations), reverse=True)
    assert sum(amounts) == Decimal("100.00")
    assert amounts[0] - amounts[-1] <= Decimal("0.01")


def test_empty_side_keeps_pool_undistributed_but_tied():
    holders = [RightsHolder("A", "recorded", Decimal("1"))]
    s = scenario(holders=holders)
    r = run_waterfall(s, Decimal("1000"))
    r.assert_conservation()
    assert r.payout("A") == r.recorded_pool
    assert r.total_paid + r.undistributed == r.royalty_pool
    assert r.undistributed_publishing == r.publishing_pool


def test_negative_revenue_is_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        run_waterfall(scenario(), Decimal("-1"))


def test_each_pool_share_must_be_in_range():
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        scenario(rec="-1", pub="2")


def test_duplicate_ids_are_rejected():
    holders = [
        RightsHolder("A", "recorded", Decimal("1"), id="same"),
        RightsHolder("B", "publishing", Decimal("1"), id="same"),
    ]
    with pytest.raises(ValueError, match="ids must be unique"):
        scenario(holders=holders)


def test_split_must_sum_to_one():
    with pytest.raises(ValueError):
        scenario(rec="0.6", pub="0.5")


def test_weights_scale_invariant():
    a = run_waterfall(scenario(), Decimal("500000"))
    doubled = [
        RightsHolder(h.name, h.side, h.weight * 2)
        for h in scenario().rightsholders
    ]
    b = run_waterfall(scenario(holders=doubled), Decimal("500000"))
    for h in ("Indie Label A", "Publisher Y"):
        assert a.payout(h) == b.payout(h)
