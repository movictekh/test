from collections.abc import Callable

from system.payments.models import ConfirmedReceipt


class PaymentReceiptApplicationError(Exception):
    """Raised when a confirmed receipt cannot be applied to its business purpose."""


_RECEIPT_APPLICATIONS: dict[str, Callable[[ConfirmedReceipt], object]] = {}


def register_receipt_application(purpose_type, handler, *, replace=False):
    normalized = (purpose_type or "").strip()
    if not normalized:
        raise PaymentReceiptApplicationError("Receipt application purpose type is required.")
    if normalized in _RECEIPT_APPLICATIONS and not replace:
        raise PaymentReceiptApplicationError(
            f"Receipt application for '{normalized}' is already registered."
        )
    _RECEIPT_APPLICATIONS[normalized] = handler
    return handler


def clear_receipt_application_registry():
    _RECEIPT_APPLICATIONS.clear()


def apply_confirmed_receipt(receipt: ConfirmedReceipt) -> bool:
    handler = _RECEIPT_APPLICATIONS.get(receipt.intent.purpose_type)
    if handler is None:
        return False
    try:
        handler(receipt)
    except Exception as exc:
        raise PaymentReceiptApplicationError(
            f"Confirmed receipt {receipt.reference} could not be applied."
        ) from exc
    return True
