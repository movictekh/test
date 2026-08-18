"""
Authentication utilities for HR Service API.

This module provides Django Ninja compatible authentication classes
that verify tokens with the main auth backend.
"""

from typing import Optional, Any
from ninja.security import HttpBearer
from django.http import HttpRequest

from .auth_client import get_auth_client, AuthClient


class AuthBearer(HttpBearer):
    """
    Django Ninja authentication class that verifies JWT tokens
    with the main auth backend service.

    Usage:
        from hr.utils.auth import AuthBearer

        router = Router(auth=AuthBearer())

        @router.get("/protected")
        def protected_endpoint(request):
            # request.auth contains user_id
            user_id = request.auth
            return {"user_id": user_id}
    """

    def authenticate(self, request: HttpRequest, token: str) -> Optional[int]:
        """
        Authenticate the request by verifying the token with auth service.
        Also fetches employee data (level/position) for permission checks.

        Args:
            request: The HTTP request
            token: The bearer token (without 'Bearer ' prefix)

        Returns:
            user_id if valid, None otherwise
        """
        client = get_auth_client()
        is_valid, user_id = client.verify_token(token)

        if is_valid and user_id:
            # Store user_id in request for later use
            request.user_id = user_id

            # Fetch employee data for context
            employee_data = client.get_employee_info(str(user_id), token)
            if employee_data:
                request.employee_id = employee_data.get('employee_id', '')
            else:
                request.employee_id = ''

            return user_id
        return None


class AuthBearerWithUser(HttpBearer):
    """
    Authentication class that also fetches full user data.

    Usage:
        from hr.utils.auth import AuthBearerWithUser

        router = Router(auth=AuthBearerWithUser())

        @router.get("/protected")
        def protected_endpoint(request):
            # request.auth contains full user data
            user_data = request.auth
            return {"email": user_data.get('email')}
    """

    def authenticate(self, request: HttpRequest, token: str) -> Optional[dict]:
        """
        Authenticate and fetch full user data.

        Returns:
            User data dict if valid, None otherwise
        """
        client = get_auth_client()
        success, user_data, message = client.get_current_user(token)

        if success and user_data:
            request.user_data = user_data
            request.user_id = user_data.get('id')
            # Store token for downstream calls
            request.auth_token = token
            return user_data
        return None


class OptionalAuthBearer(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str) -> Optional[int]:
        if not token:
            return None

        client = get_auth_client()
        is_valid, user_id = client.verify_token(token)

        if is_valid and user_id:
            request.user_id = user_id
            return user_id
        return None


# Convenience instances
auth_bearer = AuthBearer()
auth_bearer_with_user = AuthBearerWithUser()
optional_auth = OptionalAuthBearer()


def get_token_from_request(request: HttpRequest) -> Optional[str]:
    """Extract bearer token from request headers."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None


def require_auth(request: HttpRequest) -> tuple[bool, Optional[int], str]:
    """
    Verify authentication for a request.

    Returns:
        Tuple of (is_authenticated, user_id, error_message)
    """
    token = get_token_from_request(request)
    if not token:
        return False, None, "Authorization header required"

    client = get_auth_client()
    is_valid, user_id = client.verify_token(token)

    if not is_valid:
        return False, None, "Invalid or expired token"

    return True, user_id, ""
