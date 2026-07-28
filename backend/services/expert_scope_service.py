"""Shared eligibility rules for expert shipment scopes."""
from __future__ import annotations

from typing import Iterable, TypeVar

from backend.models import ExpertUser, ShipmentRequest

EXPERT_ROLES = ("expert", "business_expert")
T = TypeVar("T", bound=ExpertUser)


def is_expert_role(role: str | None) -> bool:
    return role in EXPERT_ROLES


def can_handle_request(expert: ExpertUser, shipment_request: ShipmentRequest) -> bool:
    if not expert.is_active or not is_expert_role(expert.role):
        return False
    if shipment_request.shipping_type == "international":
        return bool(expert.can_handle_international)
    return bool(expert.can_handle_domestic)


def eligible_experts(experts: Iterable[T], shipment_request: ShipmentRequest) -> list[T]:
    return [expert for expert in experts if can_handle_request(expert, shipment_request)]
