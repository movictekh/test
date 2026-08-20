import base64

import requests
from django.conf import settings


def _get_auth_token():
    """Authenticate with Monnify and return a bearer token."""
    credentials = f"{settings.MONNIFY_API_KEY}:{settings.MONNIFY_SECRET_KEY}"
    encoded = base64.b64encode(credentials.encode()).decode()

    response = requests.post(
        f"{settings.MONNIFY_BASE_URL}/api/v1/auth/login",
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        },
    )

    if response.status_code != 200:
        return None

    return response.json().get("responseBody", {}).get("token")


def monnifyPaymentVerification(transaction_reference: str, expected_amount: float) -> bool:
    """Verify a completed Monnify payment by transaction reference and expected amount."""
    try:
        token = _get_auth_token()
        if not token:
            return False

        response = requests.get(
            f"{settings.MONNIFY_BASE_URL}/api/v1/merchants/transactions/reference/{transaction_reference}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            return False

        body = response.json().get("responseBody", {})
        status = body.get("transactionStatus")
        amount_paid = body.get("amountPaid", 0)

        return status == "COMPLETED" and float(amount_paid) == float(expected_amount)
    except Exception:
        return False
