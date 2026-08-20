"""
Authentication utilities for Services Backend API.

This module provides Django Ninja compatible authentication classes
that verify tokens with the main auth backend.
"""

from typing import Optional
from ninja.security import HttpBearer
from django.http import HttpRequest

from .auth_client import get_auth_client


class AuthBearer(HttpBearer):
    """
    Django Ninja authentication class that verifies JWT tokens
    with the main auth backend service.
    """

    def authenticate(self, request: HttpRequest, token: str) -> Optional[int]:
        client = get_auth_client()
        is_valid, user_id = client.verify_token(token)

        if is_valid and user_id:
            request.user_id = user_id
            return user_id
        return None


class AuthBearerWithUser(HttpBearer):
    """Authentication class that also fetches full user data."""

    def authenticate(self, request: HttpRequest, token: str) -> Optional[dict]:
        client = get_auth_client()
        success, user_data, message = client.get_current_user(token)

        if success and user_data:
            request.user_data = user_data
            request.user_id = user_data.get('id')
            request.auth_token = token
            return user_data
        return None


class OptionalAuthBearer(HttpBearer):
    """Optional authentication - allows unauthenticated requests."""

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
