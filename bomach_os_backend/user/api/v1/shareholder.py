from ninja import Router, Query
from ninja.pagination import paginate, LimitOffsetPagination
from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from typing import List, Optional
from decimal import Decimal
import uuid

from user.api.schemas.others import MessageSchema
from user.api.schemas.shareholder import (
    ShareholderCreateSchema,
    ShareholderUpdateSchema,
    ShareholderSchema,
    ShareholderSummarySchema,
)
from user.models.shareholder import Shareholder
from user.models.user import User
from user.models.employee import Employee
from user.utils.perm import require_permission
from user.utils.send_email import send_shareholder_welcome_email
from user.utils.generate_pass import generate_password

DOMAIN = settings.DOMAIN

shareholder_api = Router(tags=["Shareholders / Board"])


@shareholder_api.get("/summary", response={200: ShareholderSummarySchema})
def get_shareholder_summary(request):
    qs = Shareholder.objects.all()
    active_qs = qs.filter(is_active=True)
    total_pct = active_qs.aggregate(total=Sum('share_percentage'))['total'] or Decimal('0.00')

    composition = [
        {
            'title': value,
            'title_display': label,
            'count': qs.filter(title=value).count(),
        }
        for value, label in Shareholder.TITLE_CHOICES
        if qs.filter(title=value).exists()
    ]

    return 200, {
        'total_shareholders': qs.count(),
        'active_shareholders': active_qs.count(),
        'total_share_percentage': total_pct,
        'unallocated_percentage': max(Decimal('0.00'), Decimal('100.00') - total_pct),
        'board_composition': composition,
    }


@shareholder_api.get("", response=List[ShareholderSchema])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("shareholders", "list")
def list_shareholders(
    request,
    is_active: Optional[bool] = Query(None),
    is_board_member: Optional[bool] = Query(None),
    title: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    qs = Shareholder.objects.select_related('user').all()

    if is_active is not None:
        qs = qs.filter(is_active=is_active)

    if is_board_member is not None:
        qs = qs.filter(is_board_member=is_board_member)

    if title:
        qs = qs.filter(title=title)

    if search:
        qs = qs.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(shareholder_id__icontains=search)
        )

    return qs


@shareholder_api.get("/{shareholder_id}", response={200: ShareholderSchema, 404: MessageSchema})
@require_permission("shareholders", "view")
def get_shareholder(request, shareholder_id: int):
    try:
        s = Shareholder.objects.select_related('user').get(id=shareholder_id)
        return 200, s
    except Shareholder.DoesNotExist:
        return 404, {"detail": "Shareholder not found"}


@shareholder_api.post("", response={201: ShareholderSchema, 400: MessageSchema})
@require_permission("shareholders", "create")
def create_shareholder(request, payload: ShareholderCreateSchema):
    try:
        password = payload.password or generate_password()
        with transaction.atomic():
            if User.objects.filter(email=payload.email).exists():
                return 400, {"detail": "A user with this email already exists"}

            username = f"{payload.email.split('@')[0]}_{uuid.uuid4().hex[:6].upper()}"

            user = User.objects.create(
                username=username,
                email=payload.email,
                password=make_password(password),
                first_name=payload.first_name,
                last_name=payload.last_name,
                gender=payload.gender,
                marital_status=payload.marital_status,
                phone_number=payload.phone_number,
                date_of_birth=payload.date_of_birth,
                address=payload.address,
                profile_picture=payload.profile_picture,
            )

            employee = Employee.objects.create(
                employee_id=f"MEM-{uuid.uuid4().hex[:12].upper()}",
                user=user,
                employment_type='full-time',
                is_active=payload.is_active,
            )

            shareholder = Shareholder.objects.create(
                user=user,
                title=payload.title,
                share_percentage=payload.share_percentage,
                share_count=payload.share_count,
                is_board_member=payload.is_board_member,
                is_active=payload.is_active,
                notes=payload.notes or "",
            )

            def send_email():
                res = send_shareholder_welcome_email(
                    password=password,
                    recipient=payload.email,
                    login_url=f"{DOMAIN}/api/v1/auth/login",
                    first_name=payload.first_name,
                )
                if res.status_code not in [200, 201]:
                    print(
                        f"Warning: Welcome email could not be sent to {user.email}. "
                        f"Response: {res.status_code} - {res.text}"
                    )

            transaction.on_commit(send_email)
            return 201, shareholder

    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@shareholder_api.put("/{shareholder_id}", response={200: ShareholderSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("shareholders", "update")
def update_shareholder(request, shareholder_id: int, payload: ShareholderUpdateSchema):
    try:
        s = Shareholder.objects.select_related('user').get(id=shareholder_id)
        data = payload.dict(exclude_unset=True)

        user_fields = {'first_name', 'last_name', 'gender', 'marital_status', 'phone_number', 'date_of_birth', 'address', 'profile_picture'}
        user_updates = {k: v for k, v in data.items() if k in user_fields}
        shareholder_updates = {k: v for k, v in data.items() if k not in user_fields}

        if user_updates:
            for field, value in user_updates.items():
                setattr(s.user, field, value)
            s.user.full_clean()
            s.user.save()

        for field, value in shareholder_updates.items():
            setattr(s, field, value)

        s.full_clean()
        s.save()
        s.refresh_from_db()

        return 200, s

    except Shareholder.DoesNotExist:
        return 404, {"detail": "Shareholder not found"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}
