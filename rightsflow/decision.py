"""The rights holder's question: should I license my catalog to an AI music platform?

This is a decision frame, not a forecast. It makes the three forces explicit
and lets you argue about the inputs instead of the arithmetic:

  1. ROYALTIES  — what the opt-in royalty stream is worth (NPV of your
     usage-proportional share of the pool).
  2. SUBSTITUTION — what staying out costs: buyers of production/sync music
     shift budget toward licensed AI catalogs you are not in. Abstaining does
     not preserve the status quo; it concedes that spend.
  3. CANNIBALIZATION — what licensing costs you: AI outputs trained on your
     catalog may displace some of your own traditional income.

License is value-positive when  royalties + avoided substitution loss
exceeds cannibalization cost. The breakeven functions invert the frame:
given your beliefs about two forces, how bad would the third have to be
to flip the decision?
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .waterfall import Scenario, run_waterfall, to_money


@dataclass(frozen=True)
class DecisionInputs:
    scenario: Scenario
    holder_name: str
    pool_gross_revenue: Decimal      # year-1 gross revenue attributable to the AI music line
    pool_growth: float               # annual growth of that revenue line
    discount_rate: float
    years: int
    addressable_income: Decimal      # holder's annual traditional income exposed to AI substitution (sync, production, library)
    terminal_substitution: float     # fraction of addressable income lost by year N if NOT licensed (linear ramp)
    cannibalization_rate: float      # fraction of addressable income lost by year N BECAUSE licensed (linear ramp)


def npv(cashflows, r: float) -> Decimal:
    """NPV of year-1..N cashflows at discount rate r (year-1 discounted once)."""
    total = Decimal("0")
    for t, cf in enumerate(cashflows, start=1):
        total += Decimal(str(cf)) / (Decimal(str(1 + r)) ** t)
    return to_money(total)


def royalty_stream(inputs: DecisionInputs) -> list[Decimal]:
    """Holder's royalty payout per year, growing with the pool."""
    year1 = run_waterfall(inputs.scenario, inputs.pool_gross_revenue).payout(inputs.holder_name)
    g = Decimal(str(1 + inputs.pool_growth))
    return [to_money(year1 * g ** (t - 1)) for t in range(1, inputs.years + 1)]


def _linear_ramp_losses(annual_income: Decimal, terminal_rate: float, years: int) -> list[Decimal]:
    """Losses ramping linearly from terminal_rate/years in year 1 to terminal_rate in year N."""
    tr = Decimal(str(terminal_rate))
    return [to_money(annual_income * tr * Decimal(t) / Decimal(years)) for t in range(1, years + 1)]


@dataclass
class DecisionResult:
    royalties_npv: Decimal
    substitution_loss_avoided_npv: Decimal
    cannibalization_cost_npv: Decimal

    @property
    def license_advantage_npv(self) -> Decimal:
        return to_money(
            self.royalties_npv + self.substitution_loss_avoided_npv - self.cannibalization_cost_npv
        )

    @property
    def verdict(self) -> str:
        return "LICENSE" if self.license_advantage_npv > 0 else "ABSTAIN"


def evaluate(inputs: DecisionInputs) -> DecisionResult:
    r = inputs.discount_rate
    return DecisionResult(
        royalties_npv=npv(royalty_stream(inputs), r),
        substitution_loss_avoided_npv=npv(
            _linear_ramp_losses(inputs.addressable_income, inputs.terminal_substitution, inputs.years), r
        ),
        cannibalization_cost_npv=npv(
            _linear_ramp_losses(inputs.addressable_income, inputs.cannibalization_rate, inputs.years), r
        ),
    )


def breakeven_cannibalization(inputs: DecisionInputs) -> float:
    """The cannibalization rate at which licensing stops paying, holding the
    royalty and substitution beliefs fixed. Loss NPV is linear in the rate, so
    this is a clean ratio."""
    base = evaluate(inputs)
    unit_loss = npv(_linear_ramp_losses(inputs.addressable_income, 1.0, inputs.years), inputs.discount_rate)
    if unit_loss == 0:
        return float("inf")
    return float((base.royalties_npv + base.substitution_loss_avoided_npv) / unit_loss)


def sensitivity_grid(inputs: DecisionInputs, growth_axis, substitution_axis):
    """license_advantage_npv over pool-growth x substitution beliefs."""
    grid = []
    for g in growth_axis:
        row = []
        for s in substitution_axis:
            probe = DecisionInputs(
                scenario=inputs.scenario,
                holder_name=inputs.holder_name,
                pool_gross_revenue=inputs.pool_gross_revenue,
                pool_growth=g,
                discount_rate=inputs.discount_rate,
                years=inputs.years,
                addressable_income=inputs.addressable_income,
                terminal_substitution=s,
                cannibalization_rate=inputs.cannibalization_rate,
            )
            row.append(evaluate(probe).license_advantage_npv)
        grid.append(row)
    return grid
