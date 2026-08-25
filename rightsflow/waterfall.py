"""Royalty waterfall for AI-music licensing pools.

Models a configurable flow of money in a hypothetical opt-in AI-music license:

    gross revenue
      -> platform retained share
      -> rights-holder royalty pool
          -> recorded-music pool / publishing pool
              -> per-rights-holder allocation, proportional to declared
                 catalog-inclusion and usage weights

Money is handled in Decimal cents with largest-remainder rounding so every
waterfall ties out exactly: payouts plus explicitly undistributed amounts equal
the pool to the cent.
An allocation that doesn't tie out is a bug, not a rounding artifact —
tests enforce this invariant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP
from typing import Iterable

CENT = Decimal("0.01")


def to_money(x) -> Decimal:
    try:
        value = Decimal(str(x))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid money value: {x!r}") from exc
    if not value.is_finite():
        raise ValueError("money values must be finite")
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


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
    id: str = ""

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("rights-holder name must not be empty")
        if not self.id:
            object.__setattr__(self, "id", self.name)
        if self.side not in ("recorded", "publishing"):
            raise ValueError(f"side must be 'recorded' or 'publishing', got {self.side!r}")
        weight = Decimal(str(self.weight))
        if not weight.is_finite() or weight < 0:
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
        if not rs.is_finite() or not pb.is_finite() or not (0 <= rs <= 1) or not (0 <= pb <= 1):
            raise ValueError("recorded_share and publishing_share must each be in [0, 1]")
        if rs + pb != 1:
            raise ValueError(f"recorded_share + publishing_share must equal 1, got {rs + pb}")
        for side in ("recorded", "publishing"):
            if self.side_holders(side) and sum(h.weight for h in self.side_holders(side)) == 0:
                raise ValueError(f"{side} side has holders but zero total weight")
        ids = [holder.id for holder in self.rightsholders]
        if len(ids) != len(set(ids)):
            raise ValueError("rights-holder ids must be unique")

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
    undistributed_recorded: Decimal = Decimal("0.00")
    undistributed_publishing: Decimal = Decimal("0.00")

    @property
    def total_paid(self) -> Decimal:
        return sum((a.amount for a in self.allocations), Decimal("0.00"))

    @property
    def undistributed(self) -> Decimal:
        return self.undistributed_recorded + self.undistributed_publishing

    def payout(self, key: str) -> Decimal:
        by_id = [a for a in self.allocations if a.holder.id == key]
        if len(by_id) == 1:
            return by_id[0].amount
        by_name = [a for a in self.allocations if a.holder.name == key]
        if len(by_name) == 1:
            return by_name[0].amount
        if len(by_name) > 1:
            raise KeyError(f"ambiguous rights-holder name {key!r}; use a unique id")
        raise KeyError(key)

    def assert_conservation(self):
        """Every level of the waterfall must tie out to the cent."""
        if self.platform_retained + self.royalty_pool != self.gross_revenue:
            raise RuntimeError("level 1 conservation failure")
        if self.recorded_pool + self.publishing_pool != self.royalty_pool:
            raise RuntimeError("level 2 conservation failure")
        if self.total_paid + self.undistributed != self.royalty_pool:
            raise RuntimeError(
                f"allocation failure: paid {self.total_paid} + undistributed "
                f"{self.undistributed} vs pool {self.royalty_pool}"
            )


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
    if gross < 0:
        raise ValueError("gross_revenue must be non-negative")
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
            amount = Decimal(side_cents) * CENT
            if side == "recorded":
                result.undistributed_recorded = amount
            else:
                result.undistributed_publishing = amount
            continue
        shares = _largest_remainder(side_cents, [Decimal(str(h.weight)) for h in holders])
        for h, c in zip(holders, shares):
            result.allocations.append(Allocation(holder=h, amount=Decimal(c) * CENT))

    result.assert_conservation()
    return result
