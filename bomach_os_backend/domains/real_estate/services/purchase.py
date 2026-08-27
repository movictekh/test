from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from domains.crm.models.client import Client
from domains.real_estate.models.estate import Property
from domains.real_estate.models.property_purchase import PropertyPurchase
from system.identity.models.user import User
from user.utils.generate_pass import generate_password
from user.utils.send_email import send_client_welcome_email


def search_purchase_clients(query: str, limit: int = 20):
    search = (query or "").strip()
    clients = Client.objects.select_related("user").filter(is_active=True)
    if search:
        clients = clients.filter(
            Q(user__email__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__phone_number__icontains=search)
            | Q(phone__icontains=search)
            | Q(company_name__icontains=search)
        )
    return clients.order_by("user__first_name", "user__last_name", "user__email")[:limit]


def _unique_username(email: str) -> str:
    base = email.split("@", 1)[0].strip() or "client"
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{counter}"
        counter += 1
    return username


@transaction.atomic
def create_purchase_client(
    *,
    email: str,
    first_name: str,
    last_name: str,
    phone_number: str | None = None,
    company_name: str | None = None,
    send_portal_invite: bool = False,
):
    normalized_email = email.strip().lower()
    first_name = first_name.strip()
    last_name = last_name.strip()
    if not first_name:
        raise ValidationError({"first_name": "First name is required."})
    if not last_name:
        raise ValidationError({"last_name": "Last name is required."})
    if User.objects.filter(email__iexact=normalized_email).exists():
        raise ValidationError({"email": "A user with this email already exists."})

    password = generate_password() if send_portal_invite else None
    user = User.objects.create_user(
        username=_unique_username(normalized_email),
        email=normalized_email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number or None,
    )
    client = Client.objects.create(
        user=user,
        phone=phone_number or "",
        company_name=(company_name or "").strip(),
    )

    if send_portal_invite:
        def send_invite():
            result = send_client_welcome_email(
                password=password,
                recipient=user.email,
                login_url="https://bomach-os-client.web.app/#/login",
                client_name=user.get_full_name() or user.email,
                password_setup_url=(
                    "https://bomach-os-client.web.app/client/setup-password"
                    f"?email={user.email}"
                ),
            )
            if result.status_code not in [200, 201]:
                print(f"Warning: purchaser portal invite could not be sent to {user.email}.")
        transaction.on_commit(send_invite)

    return client


def _reservation_snapshot(estate, agreed_price: Decimal):
    threshold = estate.reservation_threshold_percent
    if threshold is None:
        return None, None
    amount = ((agreed_price * threshold) / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return threshold, amount


@transaction.atomic
def create_property_purchase(
    *,
    property_id: int,
    client_id: int,
    mode: str,
    created_by,
    agreed_price: Decimal | None = None,
    installment_months: int | None = None,
):
    try:
        prop = Property.objects.select_for_update().select_related("estate").get(id=property_id)
    except Property.DoesNotExist as exc:
        raise ValidationError({"property_id": "Property not found."}) from exc

    if not prop.estate_id:
        raise ValidationError({"property_id": "Phase 3 requires an Estate-linked property."})
    if not prop.is_active:
        raise ValidationError({"property_id": "Inactive properties cannot be purchased."})
    if prop.status != "available":
        raise ValidationError({"property_id": "Only available properties can start a purchase."})

    try:
        client = Client.objects.select_related("user").get(id=client_id, is_active=True)
    except Client.DoesNotExist as exc:
        raise ValidationError({"client_id": "Active client not found."}) from exc

    if PropertyPurchase.objects.filter(
        property=prop, status__in=PropertyPurchase.ACTIVE_STATUSES
    ).exists():
        raise ValidationError({"property_id": "This property already has an active purchase."})

    estate = prop.estate
    price = Decimal(agreed_price if agreed_price is not None else prop.price)
    if price <= Decimal("0.00"):
        raise ValidationError({"agreed_price": "Agreed price must be greater than zero."})

    reservation_percent = None
    reservation_amount = None
    months = installment_months

    if mode == PropertyPurchase.MODE_RESERVATION:
        if not estate.reservation_allowed:
            raise ValidationError({"mode": "Reservation is disabled for this Estate."})
        reservation_percent, reservation_amount = _reservation_snapshot(estate, price)
        months = None
    elif mode == PropertyPurchase.MODE_INSTALLMENT:
        if not estate.installment_allowed:
            raise ValidationError({"mode": "Installment payment is disabled for this Estate."})
        if months is None or months < 1:
            raise ValidationError({"installment_months": "Choose a positive installment duration."})
        if estate.max_installment_months and months > estate.max_installment_months:
            raise ValidationError(
                {"installment_months": f"This Estate allows at most {estate.max_installment_months} months."}
            )
        if estate.reservation_allowed:
            reservation_percent, reservation_amount = _reservation_snapshot(estate, price)
    elif mode == PropertyPurchase.MODE_FULL_PAYMENT:
        months = None
    else:
        raise ValidationError({"mode": "Unsupported purchase mode."})

    purchase = PropertyPurchase(
        property=prop,
        client=client,
        mode=mode,
        agreed_price=price,
        reservation_threshold_percent=reservation_percent,
        reservation_amount=reservation_amount,
        installment_months=months,
        payment_window_hours=estate.reservation_payment_window_hours,
        payment_window_expires_at=(
            timezone.now() + timedelta(hours=estate.reservation_payment_window_hours)
        ),
        status=PropertyPurchase.STATUS_AWAITING_APPROVAL,
        created_by=created_by,
    )
    purchase.full_clean()
    try:
        purchase.save()
    except IntegrityError as exc:
        raise ValidationError({"property_id": "This property already has an active purchase."}) from exc

    # Agreement creation never mutates Property.status/owner/client holder or Finance.
    # Verified Central Payments receipts own later settlement transitions.
    return purchase


def get_active_property_purchase(property_id: int):
    return (
        PropertyPurchase.objects.select_related("property__estate", "client__user", "invoice", "created_by")
        .filter(property_id=property_id, status__in=PropertyPurchase.ACTIVE_STATUSES)
        .first()
    )


def get_property_purchase(purchase_id: int):
    return PropertyPurchase.objects.select_related(
        "property__estate", "client__user", "invoice", "created_by"
    ).get(id=purchase_id)
