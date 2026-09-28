"""Authoritative Cargo path resolution for allocation and ETA consumers."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from backend.extensions import db
from backend.operational_models import RouteCargoDestination, RouteLeg


class CargoRouteError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CargoRoutePath:
    mapping: RouteCargoDestination
    legs: tuple[RouteLeg, ...]

    def contains_leg(self, route_leg_id: int) -> bool:
        return any(leg.id == route_leg_id for leg in self.legs)


def _endpoint(leg: RouteLeg, side: str) -> tuple[int, int | None]:
    return (
        getattr(leg, f"{side}_location_id"),
        getattr(leg, f"{side}_logistics_point_id"),
    )


def resolve_cargo_route(cargo, route_plan_id: int) -> CargoRoutePath:
    """Resolve the exact root-to-terminal path pinned by one plan revision."""
    mapping = db.session.scalar(
        select(RouteCargoDestination).where(
            RouteCargoDestination.route_plan_id == route_plan_id,
            RouteCargoDestination.operational_shipment_id
            == cargo.operational_shipment_id,
            RouteCargoDestination.shipment_cargo_item_id == cargo.id,
        )
    )
    if mapping is None:
        raise CargoRouteError(
            "CARGO_ROUTE_REQUIRED", "Cargo has no route branch in this plan."
        )

    leg_id = mapping.destination_route_leg_id
    seen: set[int] = set()
    reverse_path: list[RouteLeg] = []
    while leg_id is not None:
        if leg_id in seen:
            raise CargoRouteError(
                "CARGO_ROUTE_INVALID", "Cargo route branch contains a cycle."
            )
        seen.add(leg_id)
        leg = db.session.scalar(
            select(RouteLeg).where(
                RouteLeg.id == leg_id, RouteLeg.route_plan_id == route_plan_id
            )
        )
        if leg is None:
            raise CargoRouteError(
                "CARGO_ROUTE_INVALID",
                "Cargo route branch contains a leg outside its plan revision.",
            )
        reverse_path.append(leg)
        leg_id = leg.parent_route_leg_id

    legs = tuple(reversed(reverse_path))
    if not legs:
        raise CargoRouteError("CARGO_ROUTE_INVALID", "Cargo route branch is empty.")
    for previous, following in zip(legs, legs[1:]):
        if _endpoint(previous, "destination") != _endpoint(following, "origin"):
            raise CargoRouteError(
                "CARGO_ROUTE_INVALID", "Cargo route branch is not continuous."
            )
    return CargoRoutePath(mapping=mapping, legs=legs)
