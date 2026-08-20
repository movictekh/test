import jwt
from ninja.security import HttpBearer
from django.http import HttpResponseForbidden
from django.conf import settings
from ninja.errors import HttpError
from user.models import TokenBlacklist, User


class JWTAuthenticator(HttpBearer):
    def authenticate(self, request, token):
        try:
            # Decode JWT token (using HS256 algorithm)
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")

            # Check if token is blacklisted
            if TokenBlacklist.is_blacklisted(token):
                raise HttpError(401, "You are logged out. Try to login again.")

            # Fetch user from the database
            user = User.objects.filter(pk=user_id).first()

            if user is None:
                raise HttpError(401, "Invalid or expired session")

            if not user.is_active:
                raise HttpError(401, "User account is inactive")

            request.user = user  # Attach user object to request

            # Set employee context for permission checks
            try:
                employee = user.employee_profile
                request.employee_id = employee.id
            except Exception:
                request.employee_id = None

            return user

        except jwt.ExpiredSignatureError:
            raise HttpError(401, "Token has expired. Try to login again.")
        except jwt.InvalidTokenError:
            raise HttpError(401, "Invalid token. Try to login again.")

    def on_auth_fail(self, response):
        return HttpResponseForbidden(
            "Failed to authenticate! or maybe you requested for a password change."
        )


def get_token_from_request(request):
    auth_header = request.headers.get("Authorization", "")
    auth_header = auth_header.replace("Bearer ", "", 1).strip()
    if not auth_header:
        return None
    return auth_header
