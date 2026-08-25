import json
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from django.db.models import Sum
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.auth import ErrorResponse
from user.api.schemas.others import MessageSchema
from user.api.schemas.wallet import TransactionResponse, WalletBalanceResponse
from user.models.user import User
from user.models.wallet import Transaction
from user.utils.auth import JWTAuthenticator
from user.utils.monnify import monnifyPaymentVerification
from system.authorization import check_obj_permission, require_permission, scope_queryset

wallet_api = Router(tags=["Wallet Management"])


@wallet_api.get(
    "/transactions/",
    response={200: List[TransactionResponse], 400: ErrorResponse},
    auth=JWTAuthenticator(),
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("wallet", "list")
def list_transactions(
    request: HttpRequest,
    user_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    try:
        transactions = Transaction.objects.select_related("user").all()

        if user_id:
            transactions = transactions.filter(user_id=user_id)

        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)

        if status:
            transactions = transactions.filter(status=status)

        if start_date:
            transactions = transactions.filter(
                date__gte=datetime.fromisoformat(start_date)
            )

        if end_date:
            transactions = transactions.filter(
                date__lte=datetime.fromisoformat(end_date)
            )

        transactions = scope_queryset(request, transactions, owner_field="user")
        return transactions
    except Exception as e:
        return 400, {"detail": str(e)}


@wallet_api.get(
    "/transactions/{transaction_id}/",
    response={200: TransactionResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("wallet", "view", owner_lookup="user")
def get_transaction(request: HttpRequest, transaction_id: int):
    """Get transaction details by ID"""
    try:
        transaction = Transaction.objects.select_related("user").get(id=transaction_id)
        check_obj_permission(request, transaction, owner_field="user")
        return transaction
    except Transaction.DoesNotExist:
        return 404, {"detail": "Transaction not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@wallet_api.get(
    "/balance/{user_id}/",
    response={200: WalletBalanceResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("wallet", "view")
def get_wallet_balance(request: HttpRequest, user_id: int):
    try:
        user = User.objects.get(id=user_id)

        # Get all completed transactions for the user
        completed_transactions = Transaction.objects.filter(
            user=user, status="completed"
        )

        # Calculate totals
        credits = completed_transactions.filter(transaction_type="credit").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        debits = completed_transactions.filter(transaction_type="debit").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        # Get transaction counts
        pending_count = Transaction.objects.filter(user=user, status="pending").count()
        completed_count = completed_transactions.count()

        # Get last transaction date
        last_transaction = (
            Transaction.objects.filter(user=user).order_by("-date").first()
        )
        last_transaction_date = last_transaction.date if last_transaction else None

        return 200, {
            "user_id": user.id,
            "user_full_name": user.get_full_name(),
            "total_credits": credits,
            "total_debits": debits,
            "current_balance": user.current_balance,
            "pending_transactions": pending_count,
            "completed_transactions": completed_count,
            "last_transaction_date": last_transaction_date,
        }
    except User.DoesNotExist:
        return 404, {"detail": "User not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@wallet_api.post("/fund-wallet-webhook/", auth=None)
def fund_wallet_webhook(request: HttpRequest):
    try:
        json_data = json.loads(request.body)
        event_data = json_data.get("eventData", {})
        transaction_reference = event_data.get("transactionReference")
        metadata = event_data.get("metaData", {})

        user_id = int(metadata["user_id"])
        amount = Decimal(metadata["amount"])

        if not monnifyPaymentVerification(transaction_reference, float(amount)):
            return {"detail": "Payment verification failed"}

        user = User.objects.get(id=user_id)

        user.current_balance += amount
        user.lifetime_deposits += amount
        user.save()

        Transaction.objects.create(
            user=user,
            amount=amount,
            transaction_type="credit",
            status="completed",
            description="Wallet funding",
            reference=transaction_reference,
        )

        return {"detail": "Success"}
    except Exception:
        return {"detail": "Failed"}
