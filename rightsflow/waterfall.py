"""Royalty waterfall for AI-music licensing pools.

Models the flow of money in an opt-in, usage-proportional AI music license
(the architecture ElevenLabs pioneered with Merlin and Kobalt in Aug 2025):

    gross revenue
      -> platform retained share
      -> rights-holder royalty pool
          -> recorded-music pool / publishing pool  (e.g. the 50/50 parity
             precedent set by the Kobalt deal and later the NMPA framework)
              -> per-rights-holder allocation, proportional to opt-in
                 catalog inclusion and usage weights

Money is handled in Decimal cents with largest-remainder rounding so every
waterfall ties out exactly: the sum of payouts equals the pool to the cent.
An allocation that doesn't tie out is a bug, not a rounding artifact —
tests enforce this invariant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Iterable

CENT = Decimal("0.01")


def to_money(x) -> Decimal:
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class RightsHolder:
    """An opted-in rights holder on one side of the split.

    weight is the usage-proportional share within its side: a composite of
    training-catalog inclusion and popularity of that catalog in generated
    outputs. Weights need not sum to anything — they are normalized within
    each side.
    """

    name: str
    side: str  # "recorded" | "publishing"
    weight: Decimal

    def __post_init__(self):
        if self.side not in ("recorded", "publishing"):
            raise ValueError(f"side must be 'recorded' or 'publishing', got {self.side!r}")
        if Decimal(str(self.weight)) < 0:
            raise ValueError(f"negative weight for {self.name}")


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    platform_share: Decimal          # fraction the platform retains, e.g. 0.55
    recorded_share: Decimal          # fraction of the royalty pool to recordings
    publishing_share: Decimal        # fraction of the royalty pool to compositions
    rightsholders: tuple[RightsHolder, ...]

    def __post_init__(self):
        ps = Decimal(str(self.platform_share))
        if not (0 <= ps < 1):
            raise ValueError("platform_share must be in [0, 1)")
        rs = Decimal(str(self.recorded_share))
        pb = Decimal(str(self.publishing_share))
        if rs + pb != 1:
            raise ValueError(f"recorded_share + publishing_share must equal 1, got {rs + pb}")
        for side in ("recorded", "publishing"):
            if self.side_holders(side) and sum(h.weight for h in self.side_holders(side)) == 0:
                raise ValueError(f"{side} side has holders but zero total weight")

    def side_holders(self, side: str) -> tuple[RightsHolder, ...]:
        return tuple(h for h in self.rightsholders if h.side == side)


@dataclass
class Allocation:
    holder: RightsHolder
    amount: Decimal


@dataclass
class WaterfallResult:
    scenario: Scenario
    gross_revenue: Decimal
    platform_retained: Decimal
    royalty_pool: Decimal
    recorded_pool: Decimal
    publishing_pool: Decimal
    allocations: list[Allocation] = field(default_factory=list)

    def payout(self, name: str) -> Decimal:
        for a in self.allocations:
            if a.holder.name == name:
                return a.amount
        raise KeyError(name)

    def assert_conservation(self):
        """Every level of the waterfall must tie out to the cent."""
        assert self.platform_retained + self.royalty_pool == self.gross_revenue, "level 1 leak"
        assert self.recorded_pool + self.publishing_pool == self.royalty_pool, "level 2 leak"
        paid = sum((a.amount for a in self.allocations), Decimal("0"))
        distributable = sum(
            pool
            for pool, side in ((self.recorded_pool, "recorded"), (self.publishing_pool, "publishing"))
            if self.scenario.side_holders(side)
        )
        assert paid == distributable, f"allocation leak: paid {paid} vs pool {distributable}"


def _largest_remainder(pool_cents: int, weights: list[Decimal]) -> list[int]:
    """Split integer cents proportionally to weights; remainder cents go to the
    largest fractional parts (ties: larger weight first, then input order).
    Guarantees sum(result) == pool_cents exactly."""
    total_w = sum(weights)
    raw = [Decimal(pool_cents) * w / total_w for w in weights]
    floors = [int(r.to_integral_value(rounding=ROUND_DOWN)) for r in raw]
    remainder = pool_cents - sum(floors)
    order = sorted(
        range(len(weights)),
        key=lambda i: (raw[i] - floors[i], weights[i], -i),
        reverse=True,
    )
    for i in order[:remainder]:
        floors[i] += 1
    return floors


def run_waterfall(scenario: Scenario, gross_revenue) -> WaterfallResult:
    gross = to_money(gross_revenue)
    gross_cents = int(gross / CENT)

    pool_cents = int(
        (Decimal(gross_cents) * (1 - Decimal(str(scenario.platform_share))))
        .to_integral_value(rounding=ROUND_HALF_UP)
    )
    platform_cents = gross_cents - pool_cents

    recorded_cents = int(
        (Decimal(pool_cents) * Decimal(str(scenario.recorded_share)))
        .to_integral_value(rounding=ROUND_HALF_UP)
    )
    publishing_cents = pool_cents - recorded_cents

    result = WaterfallResult(
        scenario=scenario,
        gross_revenue=gross,
        platform_retained=Decimal(platform_cents) * CENT,
        royalty_pool=Decimal(pool_cents) * CENT,
        recorded_pool=Decimal(recorded_cents) * CENT,
        publishing_pool=Decimal(publishing_cents) * CENT,
    )

    for side, side_cents in (("recorded", recorded_cents), ("publishing", publishing_cents)):
        holders = scenario.side_holders(side)
        if not holders:
            continue
        shares = _largest_remainder(side_cents, [Decimal(str(h.weight)) for h in holders])
        for h, c in zip(holders, shares):
            result.allocations.append(Allocation(holder=h, amount=Decimal(c) * CENT))

    result.assert_conservation()
    return result
