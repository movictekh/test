"""Project Operations email composition."""

from django.template.loader import render_to_string
from system.messaging.email.services import send_email as _send_system_email

_OPERATIONS_EMAIL = "bomachoshr@gmail.com"
_SUPPORT_PHONE = "+234 XXX XXX XXXX"


def _send_email(recipient: str, name: str, subject: str, html_content: str):
    """Internal helper to send a single email."""
    return _send_system_email(
        recipient=recipient,
        name=name,
        subject=subject,
        html_content=html_content,
    )


def send_task_assignment_email(
    recipient: str,
    assignee_name: str,
    task_title: str,
    task_description: str,
    due_date: str,
    task_url: str,
):
    """Send task assignment email to an employee/associate."""
    context = {
        "recipient": recipient,
        "assignee_name": assignee_name,
        "task_title": task_title,
        "task_description": task_description,
        "due_date": due_date,
        "task_url": task_url,
    }

    html_content = render_to_string(
        "email_template/task_assignment_email.html", context
    )
    return _send_email(
        recipient=recipient,
        name=assignee_name,
        subject="New Task Assigned: " + task_title,
        html_content=html_content,
    )


def send_associate_task_assignment_email(
    recipient: str,
    associate_name: str,
    task_title: str,
    project_name: str,
    assigned_by: str,
    due_date: str,
    task_link: str,
):
    """Send task assignment email to an associate (lawyer / surveyor)."""
    context = {
        "associate_name": associate_name,
        "task_title": task_title,
        "project_name": project_name,
        "assigned_by": assigned_by,
        "due_date": due_date,
        "task_link": task_link,
        "operations_email": _OPERATIONS_EMAIL,
        "support_phone": _SUPPORT_PHONE,
    }
    html_content = render_to_string(
        "email_template/associate_task_assignment_email.html", context
    )
    return _send_email(
        recipient=recipient,
        name=associate_name,
        subject=f"New Assignment: {task_title}",
        html_content=html_content,
    )


__all__ = [
    "send_task_assignment_email",
    "send_associate_task_assignment_email",
]
