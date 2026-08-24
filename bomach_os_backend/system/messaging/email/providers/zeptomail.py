"""Zoho ZeptoMail transport adapter.

Provider-specific transport only; business email composition remains with its existing owners in Messaging Phase 1.
"""

import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger("user.utils.send_email")

ZEPTO_URL = "https://api.zeptomail.com/v1.1/email"
FROM_ADDRESS = "noreply@bomachgroup.com"
FROM_NAME = "Bomach OS"


def send_zepto_email(to_address, to_name, subject, html_content):
    """Send a single email via Zoho ZeptoMail API."""
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": settings.ZOHOZEPTOMAIL_KEY,
    }
    payload = {
        "from": {"address": FROM_ADDRESS, "name": FROM_NAME},
        "to": [
            {
                "email_address": {
                    "address": to_address,
                    "name": to_name or to_address.split("@")[0],
                }
            }
        ],
        "subject": subject,
        "htmlbody": html_content,
    }
    response = requests.post(ZEPTO_URL, data=json.dumps(payload), headers=headers)
    if not response.ok:
        logger.warning(
            "ZeptoMail API error (%s): %s", response.status_code, response.text
        )
    return response


__all__ = ["send_zepto_email"]
