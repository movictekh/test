"""
Auth Client for Operations Service

This module provides utilities for authenticating requests using JWT tokens
and querying user/employee data directly from the user app's models.
"""

import logging
from typing import Any, Dict, Optional, Tuple

import jwt
from django.conf import settings

logger = logging.getLogger(__name__)


class AuthClientError(Exception):
    """Exception raised when auth client operations fail."""

    pass


class AuthClient:
    """
    Client for authenticating requests and fetching user/employee data
    directly from the database (monolith mode).
    """

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def verify_token(self, token: str) -> Tuple[bool, Optional[int]]:
        """
        Verify a JWT token.

        Returns:
            Tuple of (is_valid, user_id)
        """
        try:
            from user.models import TokenBlacklist

            if TokenBlacklist.is_blacklisted(token):
                return False, None

            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
            return True, user_id

        except jwt.ExpiredSignatureError:
            return False, None
        except jwt.InvalidTokenError:
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {str(e)}")
            return False, None

    def get_current_user(
        self, token: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Get current user information from token."""
        is_valid, user_id = self.verify_token(token)
        if not is_valid or not user_id:
            return False, None, "Invalid or expired token"

        try:
            from user.models import User

            user = User.objects.filter(pk=user_id, is_active=True).first()
            if not user:
                return False, None, "User not found or inactive"
            user_data = {
                "id": user.pk,
                "email": user.email,
                "full_name": user.full_name,
                "username": getattr(user, "username", ""),
                "is_active": user.is_active,
            }
            return True, user_data, "Success"
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            return False, None, f"Error: {str(e)}"

    def get_employee_info(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get employee information by employee ID."""
        try:
            from domains.people.models.employee import Employee

            employee = (
                Employee.objects.select_related("department", "branch")
                .filter(pk=employee_id)
                .first()
            )
            if not employee:
                return None
            return {
                "id": str(employee.pk),
                "employee_id": getattr(employee, "employee_id", str(employee.pk)),
                "email": getattr(employee, "email", ""),
                "full_name": getattr(employee, "full_name", ""),
                "is_active": getattr(employee, "is_active", True),
                "department_id": (
                    str(employee.department_id) if employee.department_id else ""
                ),
                "department_name": (
                    str(employee.department) if employee.department else ""
                ),
                "branch_name": (
                    str(employee.branch)
                    if hasattr(employee, "branch") and employee.branch
                    else ""
                ),
                "position": getattr(employee, "position", ""),
            }
        except Exception as e:
            logger.error(f"Error getting employee info: {str(e)}")
            return None

    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client information by client ID."""
        try:
            from domains.crm.models.client import Client

            client = Client.objects.filter(pk=client_id).first()
            if not client:
                return None
            return {
                "id": str(client.pk),
                "is_active": getattr(client, "is_active", True),
            }
        except Exception as e:
            logger.error(f"Error getting client info: {str(e)}")
            return None

    def validate_employee_id(self, employee_id: str) -> bool:
        """Check if an employee ID exists."""
        try:
            from domains.people.models.employee import Employee

            return Employee.objects.filter(pk=employee_id).exists()
        except Exception:
            return False

    def validate_client_id(self, client_id: str) -> bool:
        """Check if a client ID exists."""
        try:
            from domains.crm.models.client import Client

            return Client.objects.filter(pk=client_id).exists()
        except Exception:
            return False


# Singleton instance
_default_client: Optional[AuthClient] = None


def get_auth_client() -> AuthClient:
    """Get the default auth client instance."""
    global _default_client
    if _default_client is None:
        _default_client = AuthClient()
    return _default_client


def verify_request_token(request) -> Tuple[bool, Optional[int], str]:
    """
    Verify the token from a Django/Ninja request.

    Returns:
        Tuple of (is_valid, user_id, error_message)
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header:
        return False, None, "No authorization header"

    if not auth_header.startswith("Bearer "):
        return False, None, "Invalid authorization header format"

    token = auth_header[7:]
    client = get_auth_client()
    is_valid, user_id = client.verify_token(token)

    if not is_valid:
        return False, None, "Invalid or expired token"

    return True, user_id, ""


def get_request_user(request) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Get user information from request token."""
    auth_header = request.headers.get("Authorization", "")

    if not auth_header or not auth_header.startswith("Bearer "):
        return False, None, "Invalid authorization"

    token = auth_header[7:]
    client = get_auth_client()
    return client.get_current_user(token)
