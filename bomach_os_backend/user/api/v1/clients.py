from math import ceil
from typing import List

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from user.api.schemas.auth import ErrorResponse
from user.api.schemas.clients import (
    ClientListSchema,
    ClientProfileSchema,
    ClientResponse,
    CreateClientRequest,
    CreateLeadRequest,
    LeadResponse,
    UpdateClientRequest,
    UpdateCompanyInfoSchema,
    UpdateLeadRequest,
    UpdatePersonalInfoSchema,
)
from user.api.schemas.others import MessageSchema
from user.models import Client, Employee, Lead
from system.audit.models import AuditLog
from user.models.user import User
from system.audit.services import log_activity
from user.utils.auth import JWTAuthenticator
from user.utils.generate_pass import generate_password
from system.authorization import require_permission, scope_queryset
from user.utils.send_email import send_client_welcome_email

clients_api = Router(tags=["Client Management"])

DOMAIN = settings.DOMAIN


# ============== Lead Endpoints ==============


@clients_api.get(
    "/leads/",
    response={200: List[LeadResponse], 400: ErrorResponse},
    auth=JWTAuthenticator(),
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("leads", "list")
def list_leads(
    request: HttpRequest, search: str = None, status: str = None, source: str = None
):
    """List all leads with pagination and filtering"""
    try:
        leads = Lead.objects.select_related("assigned_to").all()

        # Apply filters
        if search:
            leads = leads.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )

        if status:
            leads = leads.filter(status=status)

        if source:
            leads = leads.filter(source=source)

        leads = scope_queryset(request, leads, branch_field="branch")
        return leads
    except Exception as e:
        return 400, {"detail": str(e)}


@clients_api.get(
    "/leads/{lead_id}/",
    response={200: LeadResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("leads", "view")
def get_lead(request: HttpRequest, lead_id: int):
    """Get lead details by ID"""
    try:
        lead = Lead.objects.select_related("assigned_to").get(id=lead_id)
        return lead
    except Lead.DoesNotExist:
        return 404, {"detail": "Lead not found"}


@clients_api.post(
    "/leads/", response={201: LeadResponse, 400: ErrorResponse}, auth=JWTAuthenticator()
)
@require_permission("leads", "create")
def create_lead(request: HttpRequest, payload: CreateLeadRequest):
    """Create a new lead"""
    try:
        assigned_to = None
        if payload.assigned_to_id:
            assigned_to = Employee.objects.get(id=payload.assigned_to_id)

        lead = Lead.objects.create(
            email=payload.email,
            first_name=payload.first_name,
            last_name=payload.last_name,
            gender=payload.gender,
            marital_status=payload.marital_status,
            address=payload.address or "",
            phone_number=payload.phone_number,
            profile_picture=payload.profile_picture,
            source=payload.source,
            status=payload.status,
            company_name=payload.company_name or "",
            interested_services=payload.interested_services,
            assigned_to=assigned_to,
            notes=payload.notes or "",
        )

        log_activity(
            audit_type=AuditLog.AuditType.ADD_LEAD,
            activity=f"New lead added: {lead.first_name} {lead.last_name} ({lead.email})",
            user=request.user,
            request=request,
            audit_status=AuditLog.AuditStatus.SUCCESS,
            metadata={
                "lead_id": lead.id,
                "lead_name": f"{lead.first_name} {lead.last_name}",
                "email": lead.email,
            },
        )
        return 201, lead
    except Exception as e:
        return 400, {"detail": str(e)}


@clients_api.put(
    "/leads/{lead_id}/",
    response={200: LeadResponse, 400: ErrorResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("leads", "update")
def update_lead(request: HttpRequest, lead_id: int, payload: UpdateLeadRequest):
    """Update lead details"""
    try:
        lead = Lead.objects.get(id=lead_id)

        # Update fields
        for field, value in payload.dict(exclude_unset=True).items():
            if field == "assigned_to_id" and value:
                lead.assigned_to = Employee.objects.get(id=value)
            elif hasattr(lead, field) and value is not None:
                setattr(lead, field, value)

        lead.save()

        return lead
    except Lead.DoesNotExist:
        return 404, {"detail": "Lead not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@clients_api.delete(
    "/leads/{lead_id}/",
    response={200: MessageSchema, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("leads", "delete")
def delete_lead(request: HttpRequest, lead_id: int):
    """Delete a lead"""
    try:
        lead = Lead.objects.get(id=lead_id)
        lead.delete()
        return 200, {"detail": "Lead deleted successfully"}
    except Lead.DoesNotExist:
        return 404, {"detail": "Lead not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


# ============== Client Endpoints ==============


@clients_api.get(
    "/clients/",
    response={200: List[ClientResponse], 400: ErrorResponse},
    auth=JWTAuthenticator(),
)
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("clients", "list")
def list_clients(request: HttpRequest, search: str = None):
    """List all clients with pagination and filtering"""
    try:
        clients = Client.objects.select_related("user").all()

        # Apply filters
        if search:
            clients = clients.filter(
                Q(user__email__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
            )

        return clients
    except Exception as e:
        return 400, {"detail": str(e)}


@clients_api.get(
    "/clients/{client_id}/",
    response={200: ClientResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("clients", "view")
def get_client(request: HttpRequest, client_id: int):
    """Get client details by ID"""
    try:
        client = Client.objects.get(user__id=client_id)
        return client
    except Client.DoesNotExist:
        return 404, {"detail": "Client not found"}


@clients_api.post(
    "/clients/",
    response={201: ClientResponse, 400: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("clients", "create")
def create_client(request: HttpRequest, payload: CreateClientRequest):
    try:
        password = generate_password()
        with transaction.atomic():
            # Check if email already exists
            if User.objects.filter(email=payload.email).exists():
                return 400, {"detail": "A user with this email already exists"}

            # Create username from email (before @ symbol)
            username = payload.email.split("@")[0]

            # Ensure username is unique by appending numbers if needed
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # Create User with provided information
            user = User.objects.create_user(
                username=username,
                email=payload.email,
                password=make_password(password),
                first_name=payload.first_name,
                last_name=payload.last_name,
                phone_number=payload.phone_number,
            )

            # Create Client profile linked to the user
            client = Client.objects.create(user=user)

            log_activity(
                audit_type=AuditLog.AuditType.ADD_CLIENT,
                activity=f"New client added: {user.get_full_name() or user.email}",
                user=request.user,
                request=request,
                audit_status=AuditLog.AuditStatus.SUCCESS,
                metadata={
                    "client_id": client.id,
                    "client_name": user.get_full_name() or user.email,
                    "email": user.email,
                },
            )

            def send_email():
                res = send_client_welcome_email(
                    password=password,
                    recipient=payload.email,
                    login_url=f"https://bomach-os-client.web.app/#/login",
                    client_name=f"{user.first_name} {user.last_name}",
                    password_setup_url=f"https://bomach-os-client.web.app/client/setup-password?email={payload.email}",
                )

                if res.status_code not in [200, 201]:
                    print(
                        f"Warning: Welcome email could not be sent to {user.email}. Response: {res.status_code} - {res.text}"
                    )

            transaction.on_commit(send_email)

        return 201, client
    except Exception as e:
        return 400, {"detail": str(e)}


@clients_api.put(
    "/clients/{client_id}/",
    response={200: ClientResponse, 400: ErrorResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("clients", "update")
def update_client(request: HttpRequest, client_id: int, payload: UpdateClientRequest):
    """Update client information"""
    try:
        # Get the client by user ID
        client = Client.objects.select_related("user").get(user__id=client_id)
        user = client.user

        # Update user fields
        update_data = payload.dict(exclude_unset=True)
        updated_fields = []

        for field, value in update_data.items():
            if hasattr(user, field) and value is not None:
                setattr(user, field, value)
                updated_fields.append(field)

        if updated_fields:
            user.save(update_fields=updated_fields)

        return client
    except Client.DoesNotExist:
        return 404, {"detail": "Client not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@clients_api.post(
    "/leads/{lead_id}/convert-to-client/",
    response={201: ClientResponse, 400: ErrorResponse, 404: ErrorResponse},
    auth=JWTAuthenticator(),
)
@require_permission("clients", "create")
def convert_lead_to_client(request: HttpRequest, lead_id: int):
    try:
        lead = Lead.objects.get(id=lead_id)

        # Check if email already exists as a user
        if User.objects.filter(email=lead.email).exists():
            return 400, {"detail": "A user with this email already exists"}

        # Use the lead's convert_to_client method which creates user, client, and deletes lead
        client = lead.convert_to_client()

        return 201, client
    except Lead.DoesNotExist:
        return 404, {"detail": "Lead not found"}
    except Exception as e:
        return 400, {"detail": str(e)}


@clients_api.get("/clients/profile", response=ClientProfileSchema)
def get_profile(request):
    client = get_object_or_404(Client, user=request.user)
    return client


@clients_api.patch("/clients/profile/personal", response=ClientProfileSchema)
def update_personal_info(request, data: UpdatePersonalInfoSchema):
    client = get_object_or_404(Client, user=request.user)

    # User model fields
    user_fields = {"first_name", "last_name"}
    user_updates = {
        k: v for k, v in data.dict(exclude_unset=True).items() if k in user_fields
    }
    if user_updates:
        User.objects.filter(pk=request.user.pk).update(**user_updates)

    # Client model fields
    client_fields = data.dict(exclude_unset=True)
    client_updates = {k: v for k, v in client_fields.items() if k not in user_fields}
    if client_updates:
        for key, value in client_updates.items():
            setattr(client, key, value)
        client.save()

    client.refresh_from_db()
    client.user.refresh_from_db()
    return client


@clients_api.patch("/clients/profile/company", response=ClientProfileSchema)
def update_company_info(request, data: UpdateCompanyInfoSchema):
    client = get_object_or_404(Client, user=request.user)

    updates = data.dict(exclude_unset=True)
    if updates:
        for key, value in updates.items():
            setattr(client, key, value)
        client.save()

    return client


@clients_api.get("/admin/clients", response=List[ClientListSchema])
def list_all_clients(request):
    return Client.objects.select_related("user").all()


@clients_api.get("/admin/clients/{client_id}", response=ClientProfileSchema)
def get_client_detail(request, client_id: int):
    return get_object_or_404(Client.objects.select_related("user"), id=client_id)
