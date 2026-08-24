
from django.template.loader import render_to_string
from system.messaging.email.providers.zeptomail import send_zepto_email as _send_zepto_email
from system.messaging.email.services import send_email as _send_system_email
from domains.project_operations.email import (
    send_associate_task_assignment_email,
    send_task_assignment_email,
)
from domains.real_estate.email import send_invoice_email






def _chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def send_email_util(
    recipients: list,
    header: str = "Bomach OS",
    title: str = "Hi there!",
    sub_title: str = "",
):
    path = ("email_template/custom.html",)
    context_data = {"title": title, "sub_title": sub_title, "header": header}
    html_content = render_to_string(path, context_data)

    responses = []
    for chunk in _chunk_list(recipients, 100):
        for recipient in chunk:
            if not recipient:
                continue
            email = recipient.get("email", "")
            name = recipient.get("name", "")
            if not email:
                continue
            resp = _send_system_email(
                recipient=email,
                name=name,
                subject=title,
                html_content=html_content,
            )
            responses.append(resp)

    return responses


def send_two_factor_code_email(recipient: str, first_name: str, code: str):
    """Send two-factor authentication code to user."""
    context = {
        "first_name": first_name,
        "code": code,
    }
    html_content = render_to_string("email_template/two_factor_code.html", context)
    return _send_email(
        recipient=recipient,
        name=first_name,
        subject="Your Bomach OS Login Verification Code",
        html_content=html_content,
    )




def _send_email(recipient: str, name: str, subject: str, html_content: str):
    """Internal helper to send a single email."""
    return _send_system_email(
        recipient=recipient,
        name=name,
        subject=subject,
        html_content=html_content,
    )


def send_marketing_email(recipient: str, name: str, subject: str, html_content: str):
    """Send a marketing email through the existing ZeptoMail sender."""
    return _send_email(
        recipient=recipient,
        name=name,
        subject=subject,
        html_content=html_content,
    )


def send_employee_welcome_email(
    recipient: str,
    first_name: str,
    password: str,
    login_url: str,
):
    """Send welcome email to a new employee."""
    context = {
        "first_name": first_name,
        "recipient": recipient,
        "password": password,
        "login_url": login_url,
    }
    html_content = render_to_string(
        "email_template/employee_welcome_email.html", context
    )
    return _send_email(
        recipient=recipient,
        name=first_name,
        subject="Your Bomach OS Employee Account is Ready",
        html_content=html_content,
    )


def send_client_welcome_email(
    recipient: str,
    client_name: str,
    password: str,
    login_url: str,
    password_setup_url: str,
):
    """Send welcome email to a new client."""
    context = {
        "client_name": client_name,
        "recipient": recipient,
        "password": password,
        "login_url": login_url,
        "password_setup_url": password_setup_url,
    }
    html_content = render_to_string("email_template/client_welcome_email.html", context)
    return _send_email(
        recipient=recipient,
        name=client_name,
        subject="Welcome to Bomach — Your Account is Ready",
        html_content=html_content,
    )




# ── Company constants used in associate / shareholder templates ──────────────
_OPERATIONS_EMAIL = "bomachoshr@gmail.com"
_COMPANY_ADDRESS = "No. 3A Isiuzo Street, Independence Layout, Enugu"
_SUPPORT_PHONE = "+234 XXX XXX XXXX"


def send_associate_welcome_email(
    recipient: str,
    associate_name: str,
    password: str,
    login_url: str,
):
    """Send welcome email to a newly onboarded associate (lawyer / surveyor)."""
    context = {
        "associate_name": associate_name,
        "email": recipient,
        "temporary_password": password,
        "login_link": login_url,
        "operations_email": _OPERATIONS_EMAIL,
        "company_address": _COMPANY_ADDRESS,
        "support_phone": _SUPPORT_PHONE,
    }
    html_content = render_to_string(
        "email_template/associate_welcome_email.html", context
    )
    return _send_email(
        recipient=recipient,
        name=associate_name,
        subject="Bomach OS Access Granted",
        html_content=html_content,
    )




def send_shareholder_welcome_email(
    recipient: str,
    first_name: str,
    password: str,
    login_url: str,
):
    """Send welcome email to a newly created shareholder / board member."""
    context = {
        "first_name": first_name,
        "recipient": recipient,
        "password": password,
        "login_url": login_url,
        "operations_email": _OPERATIONS_EMAIL,
        "company_address": _COMPANY_ADDRESS,
        "support_phone": _SUPPORT_PHONE,
    }
    html_content = render_to_string(
        "email_template/shareholder_welcome_email.html", context
    )
    return _send_email(
        recipient=recipient,
        name=first_name,
        subject="Bomach OS Board / Investor Access Granted",
        html_content=html_content,
    )
