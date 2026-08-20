import jwt
import uuid
from datetime import datetime, timedelta, timezone
from django.conf import settings
from typing import Dict, Optional, Tuple


class JWTService:
    # Token expiry times
    ACCESS_TOKEN_LIFETIME = timedelta(minutes=1000)
    REFRESH_TOKEN_LIFETIME = timedelta(days=90)

    @classmethod
    def create_tokens(cls, user_id: int) -> Dict[str, str]:
        access_token = cls._create_access_token(user_id)
        refresh_token = cls._create_refresh_token(user_id)

        return {"access": access_token, "refresh": refresh_token}

    @classmethod
    def _create_access_token(cls, user_id: int) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": user_id,
            "token_type": "access",
            "exp": now + cls.ACCESS_TOKEN_LIFETIME,
            "iat": now,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    @classmethod
    def _create_refresh_token(cls, user_id: int) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": user_id,
            "token_type": "refresh",
            "exp": now + cls.REFRESH_TOKEN_LIFETIME,
            "iat": now,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    @classmethod
    def verify_token(cls, token: str) -> Tuple[bool, Optional[int]]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
            return True, user_id
        except jwt.ExpiredSignatureError:
            return False, None
        except jwt.InvalidTokenError:
            return False, None

    @classmethod
    def refresh_access_token(cls, refresh_token: str) -> Tuple[bool, Optional[str]]:
        is_valid, user_id = cls.verify_token(refresh_token)
        if not is_valid:
            return False, None

        try:
            payload = jwt.decode(
                refresh_token, settings.SECRET_KEY, algorithms=["HS256"]
            )

            # Verify it's actually a refresh token
            if payload.get("token_type") != "refresh":
                return False, None

            new_access_token = cls._create_access_token(user_id)
            return True, new_access_token
        except jwt.InvalidTokenError:
            return False, None
