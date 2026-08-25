"""Auditable, operator-declared usage events linked to generated track IDs.

Eleven Music does not provide rights-holder attribution through this integration.
Events in this module therefore require an explicit source label and should not be
mistaken for model-derived provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from .waterfall import Scenario, WaterfallResult, run_waterfall, to_money


@dataclass(frozen=True)
class UsageEvent:
    track_id: str
    revenue: Decimal
    weights: dict[str, Decimal]
    attribution_source: str
    event_id: str = ""
    evidence_ref: str = "unspecified"

    def __post_init__(self):
        if not self.track_id.strip():
            raise ValueError("track_id must not be empty")
        if not self.event_id:
            object.__setattr__(self, "event_id", self.track_id)
        if to_money(self.revenue) < 0:
            raise ValueError("usage-event revenue must be non-negative")
        if self.attribution_source not in {"declared", "uniform_placeholder"}:
            raise ValueError("attribution_source must be declared or uniform_placeholder")
        if not self.weights:
            raise ValueError("usage-event weights must not be empty")
        for holder_id, weight in self.weights.items():
            value = Decimal(str(weight))
            if not holder_id or not value.is_finite() or value < 0:
                raise ValueError("usage-event holder ids and weights must be valid")
        if not any(Decimal(str(weight)) > 0 for weight in self.weights.values()):
            raise ValueError("usage-event must have at least one positive weight")


@dataclass
class UsageAllocation:
    events: tuple[UsageEvent, ...]
    results: tuple[WaterfallResult, ...]
    rounding_policy: str = "per_event_cent"

    @property
    def gross_revenue(self) -> Decimal:
        return sum((result.gross_revenue for result in self.results), Decimal("0.00"))

    @property
    def royalty_pool(self) -> Decimal:
        return sum((result.royalty_pool for result in self.results), Decimal("0.00"))

    @property
    def total_paid(self) -> Decimal:
        return sum((result.total_paid for result in self.results), Decimal("0.00"))

    @property
    def undistributed(self) -> Decimal:
        return sum((result.undistributed for result in self.results), Decimal("0.00"))

    def payouts(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for result in self.results:
            for allocation in result.allocations:
                holder_id = allocation.holder.id
                totals[holder_id] = totals.get(holder_id, Decimal("0.00")) + allocation.amount
        return totals

    def assert_conservation(self) -> None:
        if self.total_paid + self.undistributed != self.royalty_pool:
            raise RuntimeError("usage allocation conservation failure")


def allocate_usage(
    scenario: Scenario,
    events: list[UsageEvent],
    manifest_track_ids: set[str] | None = None,
) -> UsageAllocation:
    """Allocate declared event revenue with cent rounding at each event.

    Per-event rounding is deliberate and can differ from aggregating revenue
    before rounding. ``manifest_track_ids`` optionally validates track linkage.
    """
    known_ids = {holder.id for holder in scenario.rightsholders}
    results = []
    seen_events = set()
    for event in events:
        if event.event_id in seen_events:
            raise ValueError(f"duplicate event_id: {event.event_id}")
        seen_events.add(event.event_id)
        if manifest_track_ids is not None and event.track_id not in manifest_track_ids:
            raise ValueError(f"track_id not found in manifest: {event.track_id}")
        unknown = set(event.weights) - known_ids
        if unknown:
            raise ValueError(f"unknown rights-holder ids: {sorted(unknown)}")
        holders = tuple(
            replace(holder, weight=Decimal(str(event.weights[holder.id])))
            for holder in scenario.rightsholders
            if Decimal(str(event.weights.get(holder.id, 0))) > 0
        )
        event_scenario = replace(scenario, rightsholders=holders)
        results.append(run_waterfall(event_scenario, event.revenue))
    allocation = UsageAllocation(tuple(events), tuple(results))
    allocation.assert_conservation()
    return allocation
