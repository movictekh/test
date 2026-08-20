from ninja import Schema
from typing import Optional
from datetime import datetime
from decimal import Decimal

# ============== Transaction Schemas ==============


class CreateTransactionRequest(Schema):
    """Request schema for creating a new transaction"""

    user_id: int
    description: str
    amount: Decimal
    transaction_type: str  # 'credit' or 'debit'
    reference: Optional[str] = None


class UpdateTransactionStatusRequest(Schema):
    """Request schema for updating transaction status"""

    status: str  # 'pending', 'completed', 'failed', 'cancelled'


class TransactionResponse(Schema):
    """Response schema for transaction details"""

    id: int
    user_id: int
    user_full_name: str
    user_email: str
    date: datetime
    description: str
    amount: Decimal
    transaction_type: str
    status: str
    reference: Optional[str]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_user_id(obj):
        return obj.user.id

    @staticmethod
    def resolve_user_full_name(obj):
        return obj.user.get_full_name()

    @staticmethod
    def resolve_user_email(obj):
        return obj.user.email


class WalletBalanceResponse(Schema):
    """Response schema for wallet balance"""

    user_id: int
    user_full_name: str
    total_credits: Decimal
    total_debits: Decimal
    current_balance: Decimal
    pending_transactions: int
    completed_transactions: int
    last_transaction_date: Optional[datetime]
