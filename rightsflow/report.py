"""Plain-text reporting. ASCII only - renders anywhere, pastes anywhere."""

from __future__ import annotations

from decimal import Decimal

from .decision import DecisionInputs, DecisionResult, breakeven_cannibalization
from .waterfall import WaterfallResult


def money(x: Decimal) -> str:
    return f"${x:,.2f}"


def render_waterfall(result: WaterfallResult) -> str:
    s = result.scenario
    lines = []
    lines.append(f"SCENARIO: {s.name}")
    lines.append(f"  {s.description}")
    lines.append("")
    lines.append(f"  Gross revenue                {money(result.gross_revenue):>16}")
    lines.append(f"  Platform retained ({Decimal(str(s.platform_share)):.0%})     {money(result.platform_retained):>16}")
    lines.append(f"  Rights-holder royalty pool   {money(result.royalty_pool):>16}")
    lines.append(f"    Recorded pool ({Decimal(str(s.recorded_share)):.0%})       {money(result.recorded_pool):>16}")
    lines.append(f"    Publishing pool ({Decimal(str(s.publishing_share)):.0%})     {money(result.publishing_pool):>16}")
    lines.append("")
    lines.append(f"  {'RIGHTS HOLDER':<28}{'SIDE':<12}{'WEIGHT':>8}{'PAYOUT':>16}")
    for a in result.allocations:
        lines.append(
            f"  {a.holder.name:<28}{a.holder.side:<12}{Decimal(str(a.holder.weight)):>8}{money(a.amount):>16}"
        )
    paid = sum((a.amount for a in result.allocations), Decimal("0"))
    lines.append(f"  {'':<48}{'-' * 16:>16}")
    lines.append(f"  {'TOTAL PAID (ties to pool)':<48}{money(paid):>16}")
    return "\n".join(lines)


def render_decision(inputs: DecisionInputs, result: DecisionResult) -> str:
    lines = []
    lines.append(f"DECISION LENS: {inputs.holder_name}")
    lines.append(
        f"  ({inputs.years}yr horizon, {inputs.discount_rate:.0%} discount, pool growth {inputs.pool_growth:.0%}, "
        f"addressable income {money(inputs.addressable_income)}/yr)"
    )
    lines.append("")
    lines.append(f"  + Royalty stream NPV                     {money(result.royalties_npv):>16}")
    lines.append(f"  + Substitution loss avoided NPV          {money(result.substitution_loss_avoided_npv):>16}")
    lines.append(f"    (staying out concedes AI-shifted spend at {inputs.terminal_substitution:.0%} terminal)")
    lines.append(f"  - Cannibalization cost NPV               {money(result.cannibalization_cost_npv):>16}")
    lines.append(f"    (licensed outputs displacing own income at {inputs.cannibalization_rate:.0%} terminal)")
    lines.append(f"  {'':<41}{'-' * 16:>16}")
    lines.append(f"  = License advantage NPV                  {money(result.license_advantage_npv):>16}")
    lines.append("")
    be = breakeven_cannibalization(inputs)
    lines.append(f"  VERDICT: {result.verdict}")
    lines.append(
        f"  Breakeven cannibalization: {be:.1%} terminal - licensing pays unless AI outputs "
        f"displace more than {be:.1%} of this holder's addressable income by year {inputs.years}."
        if be != float("inf")
        else "  Breakeven cannibalization: n/a (no addressable income at risk)"
    )
    return "\n".join(lines)


def render_sensitivity(growth_axis, substitution_axis, grid) -> str:
    lines = []
    lines.append("SENSITIVITY: license advantage NPV  (rows: pool growth / cols: terminal substitution)")
    header = "  " + f"{'':>8}" + "".join(f"{s:>14.0%}" for s in substitution_axis)
    lines.append(header)
    for g, row in zip(growth_axis, grid):
        lines.append("  " + f"{g:>8.0%}" + "".join(f"{money(v):>14}" for v in row))
    return "\n".join(lines)
