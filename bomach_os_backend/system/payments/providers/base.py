from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Mapping, Protocol


class PaymentProviderError(Exception):
    """Base error raised by provider adapters."""


class PaymentProviderVerificationError(PaymentProviderError):
    """Raised when a provider event cannot be authenticated or verified."""


@dataclass(frozen=True)
class ProviderAttemptRequest:
    intent_reference: str
    attempt_reference: str
    amount: Decimal
    currency: str
    description: str
    metadata: dict
    idempotency_key: str


@dataclass(frozen=True)
class ProviderAttemptResult:
    provider_reference: str
    status: str = "pending"
    checkout_url: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class VerifiedProviderPayment:
    event_key: str
    event_type: str
    provider_reference: str
    intent_reference: str
    amount: Decimal
    currency: str
    paid_at: datetime
    payment_method: str = ""
    metadata: dict = field(default_factory=dict)


class PaymentProvider(Protocol):
    name: str

    def create_attempt(self, request: ProviderAttemptRequest) -> ProviderAttemptResult:
        ...

    def verify_event(
        self,
        *,
        payload: dict,
        headers: Mapping[str, str],
    ) -> VerifiedProviderPayment:
        ...
