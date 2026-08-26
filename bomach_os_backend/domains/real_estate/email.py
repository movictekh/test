"""Real Estate email composition."""

from django.template.loader import render_to_string
from system.messaging.email.services import send_email as _send_system_email


def send_invoice_email(email: str, name: str, invoice):
    """Send estate property invoice to a client via email."""

    items = []
    for item in invoice.estate_invoice_items.select_related(
        "property", "property__estate"
    ).all():
        items.append(
            {
                "property_name": item.property.property_name,
                "estate_name": f"{item.property.estate.estate_name} - {item.property.estate.developer_company_name}",
                "quantity": item.quantity,
                "unit_price": f"{item.unit_price:,.2f}",
                "total": f"{item.total:,.2f}",
            }
        )

    context_data = {
        "invoice_number": invoice.invoice_number,
        "issue_date": invoice.issue_date.strftime("%d %b %Y"),
        "due_date": invoice.due_date.strftime("%d %b %Y"),
        "client_name": name,
        "client_address": "",
        "items": items,
        "subtotal": f"{invoice.subtotal:,.2f}",
        "tax_rate": f"{invoice.tax_rate:g}",
        "tax_amount": f"{invoice.tax_amount:,.2f}",
        "total_amount": f"{invoice.total_amount:,.2f}",
        "amount_paid": invoice.amount_paid,
        "balance": f"{invoice.balance:,.2f}" if invoice.amount_paid > 0 else None,
        "notes": invoice.notes or "Thank you for your business.",
        "bank_name": invoice.bank_name or "",
        "account_name": invoice.account_name or "",
        "account_number": invoice.account_number or "",
        "sort_code": invoice.sort_code or "",
    }

    html_content = render_to_string("email_template/estate_invoice.html", context_data)

    return _send_system_email(
        recipient=email,
        name=name,
        subject=f"Invoice {invoice.invoice_number} - Bomach Engineering Services",
        html_content=html_content,
    )


__all__ = ["send_invoice_email"]
