from decimal import Decimal

import pytest

from rightsflow.decision import (
    DecisionInputs,
    breakeven_cannibalization,
    evaluate,
    npv,
    sensitivity_grid,
)
from rightsflow.waterfall import RightsHolder, Scenario


def scenario():
    return Scenario(
        name="t", description="t",
        platform_share=Decimal("0.55"),
        recorded_share=Decimal("0.5"),
        publishing_share=Decimal("0.5"),
        rightsholders=(
            RightsHolder("Indie Label A", "recorded", Decimal("5")),
            RightsHolder("Indie Label B", "recorded", Decimal("5")),
            RightsHolder("Publisher X", "publishing", Decimal("1")),
        ),
    )


def inputs(**over):
    base = dict(
        scenario=scenario(),
        holder_name="Indie Label A",
        pool_gross_revenue=Decimal("1000000"),
        pool_growth=0.0,
        discount_rate=0.10,
        years=3,
        addressable_income=Decimal("1000000"),
        terminal_substitution=0.10,
        cannibalization_rate=0.03,
    )
    base.update(over)
    return DecisionInputs(**base)


def test_npv_known_value():
    # 100 for 3 years at 10%: 90.91 + 82.64 + 75.13 = 248.68 (cent-rounded terms sum)
    assert npv([100, 100, 100], 0.10) == Decimal("248.69")


def test_royalties_reflect_waterfall_share():
    res = evaluate(inputs(pool_growth=0.0))
    # year-1 payout: 1,000,000 * 0.45 * 0.5 * (5/10) = 112,500 flat for 3 years at 10%
    assert res.royalties_npv == npv([112500, 112500, 112500], 0.10)


def test_license_advantage_increases_with_substitution_belief():
    low = evaluate(inputs(terminal_substitution=0.02)).license_advantage_npv
    high = evaluate(inputs(terminal_substitution=0.30)).license_advantage_npv
    assert high > low


def test_license_advantage_decreases_with_cannibalization():
    low = evaluate(inputs(cannibalization_rate=0.0)).license_advantage_npv
    high = evaluate(inputs(cannibalization_rate=0.50)).license_advantage_npv
    assert high < low


def test_breakeven_flips_the_verdict():
    be = breakeven_cannibalization(inputs())
    just_under = evaluate(inputs(cannibalization_rate=be * 0.999))
    just_over = evaluate(inputs(cannibalization_rate=be * 1.001))
    assert just_under.license_advantage_npv > 0
    assert just_over.license_advantage_npv < 0


def test_sensitivity_grid_shape_and_monotonicity():
    growth_axis = [0.0, 0.5]
    sub_axis = [0.0, 0.10, 0.20]
    grid = sensitivity_grid(inputs(), growth_axis, sub_axis)
    assert len(grid) == 2 and all(len(row) == 3 for row in grid)
    assert grid[1][0] > grid[0][0]          # more growth -> more royalties
    assert grid[0][2] > grid[0][0]          # more substitution risk -> licensing worth more


@pytest.mark.parametrize(
    "override, message",
    [
        ({"years": 0}, "years"),
        ({"discount_rate": -1}, "discount_rate"),
        ({"discount_rate": float("inf")}, "discount_rate"),
        ({"discount_rate": float("nan")}, "discount_rate"),
        ({"pool_growth": -1}, "pool_growth"),
        ({"pool_growth": float("inf")}, "pool_growth"),
        ({"terminal_substitution": 1.1}, "terminal_substitution"),
        ({"cannibalization_rate": -0.1}, "cannibalization_rate"),
        ({"substitution_avoidance_fraction": 1.1}, "substitution_avoidance_fraction"),
        ({"pool_gross_revenue": Decimal("-1")}, "pool_gross_revenue"),
        ({"addressable_income": Decimal("-1")}, "addressable_income"),
    ],
)
def test_invalid_decision_inputs_are_rejected(override, message):
    with pytest.raises(ValueError, match=message):
        inputs(**override)


def test_partial_substitution_avoidance_is_explicit():
    full = evaluate(inputs(substitution_avoidance_fraction=1.0))
    partial = evaluate(inputs(substitution_avoidance_fraction=0.5))
    assert partial.substitution_loss_avoided_npv < full.substitution_loss_avoided_npv
