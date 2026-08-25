from decimal import Decimal
from typing import List

from django.db.models import Q, Sum
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from system.identity.api.v1.schemas.auth import ErrorResponse
from user.api.schemas.client_inventory import (
    CreateInventoryItemRequest,
    InventoryItemResponse,
    UpdateInventoryItemRequest,
)
from user.api.schemas.others import MessageSchema
from user.models.client_inventory import CLientInventoryItem
from system.identity.authentication import JWTAuthenticator
from system.authorization import require_permission

inventory_api = Router(tags=["Client Inventory"])


@inventory_api.get(
    "/",
    response={200: List[InventoryItemResponse], 400: ErrorResponse},
    auth=JWTAuthenticator(),
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("client_inventory", "list")
def list_inventory_items(
    request: HttpRequest, search: str = None, status: str = None, unit: str = None
):
    try:
        items = CLientInventoryItem.objects.all()

        if search:
            items = items.filter(Q(item_name__icontains=search))

        if status:
            items = items.filter(status=status)

        if unit:
            items = items.filter(unit=unit)

        return items
    except Exception as e:
        return 400, {"detail": str(e)}


@inventory_api.get(
    "/{item_id}/",
    response={200: InventoryItemResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("client_inventory", "view")
def get_inventory_item(request: HttpRequest, item_id: int):
    try:
        item = CLientInventoryItem.objects.get(id=item_id)
        return 200, item
    except CLientInventoryItem.DoesNotExist:
        return 404, {"detail": "Inventory item not found"}


@inventory_api.post(
    "/",
    response={201: InventoryItemResponse, 400: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("client_inventory", "create")
def create_inventory_item(request: HttpRequest, payload: CreateInventoryItemRequest):
    try:
        # Validate unit
        if payload.unit not in [
            choice[0] for choice in CLientInventoryItem.UNIT_CHOICES
        ]:
            return 400, {
                "detail": f"Invalid unit. Must be one of: {', '.join([c[0] for c in CLientInventoryItem.UNIT_CHOICES])}"
            }

        # Validate status
        if payload.status not in [
            choice[0] for choice in CLientInventoryItem.STATUS_CHOICES
        ]:
            return 400, {
                "detail": f"Invalid status. Must be one of: {', '.join([c[0] for c in CLientInventoryItem.STATUS_CHOICES])}"
            }

        # Validate quantity and total_value
        if payload.quantity < 0:
            return 400, {"detail": "Quantity must be non-negative"}

        if payload.total_value < 0:
            return 400, {"detail": "Total value must be non-negative"}

        # Create item
        item = CLientInventoryItem.objects.create(
            item_name=payload.item_name,
            quantity=payload.quantity,
            quantity_used=payload.quantity_used or Decimal("0.00"),
            unit=payload.unit,
            total_value=payload.total_value,
            status=payload.status,
        )

        return 201, item
    except Exception as e:
        return 400, {"detail": str(e)}


@inventory_api.put(
    "/{item_id}/",
    response={200: InventoryItemResponse, 400: ErrorResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("client_inventory", "update")
def update_inventory_item(
    request: HttpRequest, item_id: int, payload: UpdateInventoryItemRequest
):
    try:
        item = CLientInventoryItem.objects.get(id=item_id)

        # Update fields
        update_data = payload.dict(exclude_unset=True)

        # Validate unit if provided
        if "unit" in update_data and update_data["unit"]:
            if update_data["unit"] not in [
                choice[0] for choice in CLientInventoryItem.UNIT_CHOICES
            ]:
                return 400, {
                    "detail": f"Invalid unit. Must be one of: {', '.join([c[0] for c in CLientInventoryItem.UNIT_CHOICES])}"
                }

        # Validate status if provided
        if "status" in update_data and update_data["status"]:
            if update_data["status"] not in [
                choice[0] for choice in CLientInventoryItem.STATUS_CHOICES
            ]:
                return 400, {
                    "detail": f"Invalid status. Must be one of: {', '.join([c[0] for c in CLientInventoryItem.STATUS_CHOICES])}"
                }

        # Validate quantity if provided
        if "quantity" in update_data and update_data["quantity"] is not None:
            if update_data["quantity"] < 0:
                return 400, {"detail": "Quantity must be non-negative"}

            if (
                "quantity_used" in update_data
                and update_data["quantity_used"] is not None
            ):
                if update_data["quantity"] < update_data["quantity_used"]:
                    return 400, {
                        "detail": "Quantity used must be less than or equal to total quantity"
                    }

        if "quantity_used" in update_data and update_data["quantity_used"] is not None:
            if update_data["quantity_used"] < 0:
                return 400, {"detail": "Quantity used must be non-negative"}

        # Validate total_value if provided
        if "total_value" in update_data and update_data["total_value"] is not None:
            if update_data["total_value"] < 0:
                return 400, {"detail": "Total value must be non-negative"}

        # Apply updates
        for field, value in update_data.items():
            if value is not None:
                setattr(item, field, value)

        item.save()

        return 200, item
    except CLientInventoryItem.DoesNotExist:
        return 404, {"detail": "Inventory item not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@inventory_api.delete(
    "/{item_id}/",
    response={200: MessageSchema, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("client_inventory", "delete")
def delete_inventory_item(request: HttpRequest, item_id: int):
    try:
        item = CLientInventoryItem.objects.get(id=item_id)
        item_name = item.item_name
        item.delete()
        return 200, {"detail": f"Inventory item '{item_name}' deleted successfully"}
    except CLientInventoryItem.DoesNotExist:
        return 404, {"detail": "Inventory item not found"}
