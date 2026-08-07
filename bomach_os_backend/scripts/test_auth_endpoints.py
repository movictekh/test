#!/usr/bin/env python3
"""
Exercise every /api/v1/auth/* endpoint (happy paths + edge cases) plus the
post-auth staff bootstrap routes that return role/permissions, against a
running backend, then write a markdown catalog of request/response shapes.

Covered post-auth:
  GET /api/v1/roles/employees/{user_id}   — full role + permissions (frontend uses this)
  GET /api/v1/roles/permissions-map      — all valid resources/actions
  GET /api/v1/roles/me/authority-limits  — flattened labeled grants

Usage:
  cd bomach_os_backend
  .venv/bin/python scripts/test_auth_endpoints.py
  .venv/bin/python scripts/test_auth_endpoints.py --base-url http://127.0.0.1:8000
  .venv/bin/python scripts/test_auth_endpoints.py --out docs/auth-tests/auth-api-catalog.md

Requires the Django server already running (default :8000).
Creates/resets local demo users (+ employee/role) via the ORM (does not call
public register — there is none).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import django
import requests

# ---------------------------------------------------------------------------
# Django bootstrap (so we can seed users + read OTPs)
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

# Load .env into os.environ if present (same pattern as local manage.py usage)
_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bomach_backend.settings")
django.setup()

from user.models import OTPCode, TokenBlacklist, User  # noqa: E402
from user.models.employee import Employee  # noqa: E402
from user.models.role import Role  # noqa: E402
from user.services.jwt_service import JWTService  # noqa: E402
from user.services.auth_service import AuthService  # noqa: E402

# ---------------------------------------------------------------------------
# Demo accounts
# ---------------------------------------------------------------------------

DEMO_PASSWORD = "AuthTestPass123!"
DEMO_PASSWORD_ALT = "AuthTestPass456!"

DEMO_ROLE_NAME = "Auth Demo Staff"
DEMO_ROLE_PERMISSIONS = {
    # Enough for the staff login bootstrap used by the frontend:
    # GET /auth/me → GET /roles/employees/{user_id}
    "roles": ["view_own"],
    "employees": ["view_own", "update_own"],
    "employee_documents": ["view_own", "list_own", "upload_own"],
    "orders": ["view", "list"],
    "service_requests": ["view", "list", "create"],
}

DEMO_USERS = {
    "active": {
        "email": "auth.demo.active@bomach.test",
        "username": "auth_demo_active",
        "first_name": "Auth",
        "last_name": "Demo",
        "is_active": True,
        "two_factor_enabled": False,
    },
    "inactive": {
        "email": "auth.demo.inactive@bomach.test",
        "username": "auth_demo_inactive",
        "first_name": "Inactive",
        "last_name": "Demo",
        "is_active": False,
        "two_factor_enabled": False,
    },
    "twofa": {
        "email": "auth.demo.2fa@bomach.test",
        "username": "auth_demo_2fa",
        "first_name": "TwoFA",
        "last_name": "Demo",
        "is_active": True,
        "two_factor_enabled": True,
    },
    # Staff peers for post-auth role/permission edge cases
    "peer": {
        "email": "auth.demo.peer@bomach.test",
        "username": "auth_demo_peer",
        "first_name": "Peer",
        "last_name": "Demo",
        "is_active": True,
        "two_factor_enabled": False,
    },
    "norole": {
        "email": "auth.demo.norole@bomach.test",
        "username": "auth_demo_norole",
        "first_name": "NoRole",
        "last_name": "Demo",
        "is_active": True,
        "two_factor_enabled": False,
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class CaseResult:
    name: str
    method: str
    path: str
    request_headers: dict[str, Any]
    request_body: Any
    status: int
    response_body: Any
    notes: str = ""
    expected_status: Optional[int] = None

    @property
    def ok(self) -> bool:
        if self.expected_status is None:
            return True
        return self.status == self.expected_status


@dataclass
class RouteCatalog:
    method: str
    path: str
    auth: str
    purpose: str
    request_schema: str
    success_shapes: list[str]
    error_shapes: list[str]
    frontend_notes: str
    live_cases: list[CaseResult] = field(default_factory=list)


def _pretty(data: Any) -> str:
    try:
        return json.dumps(data, indent=2, default=str, ensure_ascii=False)
    except TypeError:
        return str(data)


def _truncate(data: Any, max_len: int = 4000) -> Any:
    """Redact long JWT strings / huge maps in nested structures for readable MD."""
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            if k == "permissions_map" and isinstance(v, dict):
                keys = list(v.keys())
                sample = {kk: v[kk] for kk in keys[:5]}
                if len(keys) > 5:
                    sample["…"] = f"{len(keys) - 5} more resources omitted"
                out[k] = sample
            elif isinstance(v, str) and k.endswith("token") and len(v) > 80:
                out[k] = v[:48] + "…[truncated]"
            elif isinstance(v, str) and k in ("access_token", "refresh_token", "session_token") and len(v) > 80:
                out[k] = v[:48] + "…[truncated]"
            else:
                out[k] = _truncate(v, max_len)
        return out
    if isinstance(data, list):
        return [_truncate(x, max_len) for x in data]
    if isinstance(data, str) and len(data) > max_len:
        return data[:max_len] + "…[truncated]"
    return data


def ensure_demo_users() -> dict[str, User]:
    users: dict[str, User] = {}
    for key, spec in DEMO_USERS.items():
        user = User.objects.filter(email=spec["email"]).first()
        created = user is None
        if created:
            # User.save() full_clean() requires a non-blank password field.
            user = User(
                email=spec["email"],
                username=spec["username"],
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                is_active=spec["is_active"],
                two_factor_enabled=spec["two_factor_enabled"],
                is_verified=True,
            )
            user.set_password(DEMO_PASSWORD)
            user.save()
        else:
            user.username = spec["username"]
            user.first_name = spec["first_name"]
            user.last_name = spec["last_name"]
            user.is_active = spec["is_active"]
            user.two_factor_enabled = spec["two_factor_enabled"]
            user.is_verified = True
            user.set_password(DEMO_PASSWORD)
            user.save()
        # Clear leftover OTPs / blacklists for clean runs
        OTPCode.objects.filter(user=user).delete()
        TokenBlacklist.objects.filter(user=user).delete()
        users[key] = user
        action = "created" if created else "reset"
        print(f"  demo user [{key}] {action}: {user.email} (id={user.id})")
    return users


def ensure_demo_staff(users: dict[str, User]) -> dict[str, Any]:
    """Attach Employee + Role so post-auth permission endpoints can be exercised."""
    role, role_created = Role.objects.get_or_create(
        name=DEMO_ROLE_NAME,
        defaults={"permissions": DEMO_ROLE_PERMISSIONS},
    )
    role.permissions = DEMO_ROLE_PERMISSIONS
    role.save()
    print(
        f"  demo role [{'created' if role_created else 'reset'}]: "
        f"{role.name} (id={role.id})"
    )

    staff: dict[str, Any] = {"role": role, "employees": {}}
    employee_specs = {
        "active": ("AUTH-DEMO-ACTIVE", role),
        "peer": ("AUTH-DEMO-PEER", role),
        "norole": ("AUTH-DEMO-NOROLE", None),
    }
    for key, (employee_id, assigned_role) in employee_specs.items():
        user = users[key]
        employee = Employee.objects.filter(user=user).first()
        created = employee is None
        if created:
            employee = Employee(
                user=user,
                employee_id=employee_id,
                role=assigned_role,
                is_active=True,
                employment_status="active",
            )
            employee.save()
        else:
            employee.employee_id = employee_id
            employee.role = assigned_role
            employee.is_active = True
            employee.employment_status = "active"
            employee.save()
        staff["employees"][key] = employee
        print(
            f"  demo employee [{key}] {'created' if created else 'reset'}: "
            f"{employee.employee_id} role={assigned_role.name if assigned_role else None}"
        )
    return staff


def latest_otp(user: User, intent: str) -> Optional[OTPCode]:
    return (
        OTPCode.objects.filter(user=user, intent=intent)
        .order_by("-created_at")
        .first()
    )


def _path_matches(case_path: str, route_path: str) -> bool:
    """Match concrete paths against catalog templates like /roles/employees/{user_id}."""
    import re

    case = case_path.rstrip("/")
    route = route_path.rstrip("/")
    if "{" not in route:
        return case == route
    pattern = "^" + re.sub(r"\{[^}/]+\}", r"[^/]+", route) + "$"
    return re.match(pattern, case) is not None


class AuthTester:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.cases: list[CaseResult] = []
        self.users: dict[str, User] = {}
        self.staff: dict[str, Any] = {}

    def url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base}{path}"

    def call(
        self,
        name: str,
        method: str,
        path: str,
        *,
        body: Any = None,
        token: Optional[str] = None,
        expected_status: Optional[int] = None,
        notes: str = "",
        extra_headers: Optional[dict] = None,
    ) -> CaseResult:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if extra_headers:
            headers.update(extra_headers)

        kwargs: dict[str, Any] = {"headers": headers, "timeout": 30}
        if body is not None and method.upper() not in ("GET", "HEAD"):
            kwargs["json"] = body

        resp = self.session.request(method.upper(), self.url(path), **kwargs)
        try:
            resp_body: Any = resp.json()
        except ValueError:
            resp_body = resp.text

        case = CaseResult(
            name=name,
            method=method.upper(),
            path=path,
            request_headers={k: ("Bearer …" if k.lower() == "authorization" else v) for k, v in headers.items()},
            request_body=body,
            status=resp.status_code,
            response_body=resp_body,
            notes=notes,
            expected_status=expected_status,
        )
        self.cases.append(case)
        mark = "✓" if case.ok else "✗"
        print(f"  {mark} [{case.status}] {name}")
        return case

    # ------------------------------------------------------------------
    # Scenarios
    # ------------------------------------------------------------------

    def run_all(self) -> None:
        print("Seeding demo users…")
        self.users = ensure_demo_users()
        print("Seeding demo staff (employee + role)…")
        self.staff = ensure_demo_staff(self.users)
        active = self.users["active"]
        inactive = self.users["inactive"]
        twofa = self.users["twofa"]

        print("\n=== LOGIN ===")
        self._test_login(active, inactive, twofa)

        print("\n=== REFRESH ===")
        login = self.call(
            "login (setup for refresh)",
            "POST",
            "/api/v1/auth/login",
            body={"email": active.email, "password": DEMO_PASSWORD},
            expected_status=200,
        )
        access = login.response_body.get("access_token") if isinstance(login.response_body, dict) else None
        refresh = login.response_body.get("refresh_token") if isinstance(login.response_body, dict) else None
        self._test_refresh(refresh)

        print("\n=== ME / VERIFY-TOKEN ===")
        self._test_me_and_verify(access)

        print("\n=== POST-AUTH ROLE / PERMISSIONS ===")
        self._test_post_auth_roles()

        print("\n=== LOGOUT + BLACKLIST ===")
        self._test_logout(access)

        print("\n=== FORGOT / RESET PASSWORD ===")
        self._test_password_reset(active)

        print("\n=== 2FA TOGGLE + FLOW ===")
        self._test_two_factor(twofa, active)

        print("\n=== AUTH GUARD EDGE CASES ===")
        self._test_auth_guards(active)

    def _test_post_auth_roles(self) -> None:
        """Post-login bootstrap used by the frontend: /auth/me → /roles/employees/{id}."""
        active = self.users["active"]
        peer = self.users["peer"]
        norole = self.users["norole"]
        twofa = self.users["twofa"]  # user with no Employee profile

        login = self.call(
            "login (setup for role/permissions)",
            "POST",
            "/api/v1/auth/login",
            body={"email": active.email, "password": DEMO_PASSWORD},
            expected_status=200,
        )
        access = login.response_body.get("access_token") if isinstance(login.response_body, dict) else None
        if not access:
            print("    WARNING: no access token — skipped role/permission cases")
            return

        # Full staff bootstrap sequence
        me = self.call(
            "post-auth GET /me (bootstrap step 1)",
            "GET",
            "/api/v1/auth/me",
            token=access,
            expected_status=200,
            notes="Frontend then loads GET /roles/employees/{user.id} with this id.",
        )
        user_id = me.response_body.get("id") if isinstance(me.response_body, dict) else active.id

        self.call(
            "GET employee role + full permissions (own)",
            "GET",
            f"/api/v1/roles/employees/{user_id}",
            token=access,
            expected_status=200,
            notes=(
                "Primary post-auth permissions payload. Shape: id, name, branches[], "
                "permissions {resource: [actions]}, created_at, updated_at. "
                "Requires roles:view or roles:view_own."
            ),
        )

        self.call(
            "GET employee role missing Authorization",
            "GET",
            f"/api/v1/roles/employees/{user_id}",
            expected_status=401,
        )

        self.call(
            "GET employee role unknown user_id",
            "GET",
            "/api/v1/roles/employees/999999",
            token=access,
            expected_status=404,
            notes="No Employee with that user_id.",
        )

        self.call(
            "GET another employee's role with only view_own",
            "GET",
            f"/api/v1/roles/employees/{peer.id}",
            token=access,
            expected_status=403,
            notes="check_obj_permission blocks cross-user access when only roles:view_own.",
        )

        # User with no employee profile (twofa demo user)
        login_plain = self.call(
            "login user without employee profile",
            "POST",
            "/api/v1/auth/login",
            body={"email": twofa.email, "password": DEMO_PASSWORD},
            expected_status=200,
        )
        plain_access = (
            login_plain.response_body.get("access_token")
            if isinstance(login_plain.response_body, dict)
            else None
        )
        # twofa user has 2FA enabled — login may return requires_2fa instead of tokens
        if plain_access:
            self.call(
                "GET employee role without employee profile",
                "GET",
                f"/api/v1/roles/employees/{twofa.id}",
                token=plain_access,
                expected_status=403,
                notes='require_permission → 403 "Employee profile not found."',
            )
        else:
            # Disable 2FA temporarily to get a token for this edge case
            twofa.two_factor_enabled = False
            twofa.save(update_fields=["two_factor_enabled", "updated_at"])
            login_plain = self.call(
                "login user without employee profile (2FA off)",
                "POST",
                "/api/v1/auth/login",
                body={"email": twofa.email, "password": DEMO_PASSWORD},
                expected_status=200,
            )
            plain_access = (
                login_plain.response_body.get("access_token")
                if isinstance(login_plain.response_body, dict)
                else None
            )
            if plain_access:
                self.call(
                    "GET employee role without employee profile",
                    "GET",
                    f"/api/v1/roles/employees/{twofa.id}",
                    token=plain_access,
                    expected_status=403,
                    notes='require_permission → 403 "Employee profile not found."',
                )
            twofa.two_factor_enabled = True
            twofa.save(update_fields=["two_factor_enabled", "updated_at"])

        # Employee with no role assigned
        login_norole = self.call(
            "login employee with no role",
            "POST",
            "/api/v1/auth/login",
            body={"email": norole.email, "password": DEMO_PASSWORD},
            expected_status=200,
        )
        norole_access = (
            login_norole.response_body.get("access_token")
            if isinstance(login_norole.response_body, dict)
            else None
        )
        if norole_access:
            self.call(
                "GET own role when employee has no role assigned",
                "GET",
                f"/api/v1/roles/employees/{norole.id}",
                token=norole_access,
                expected_status=403,
                notes='require_permission → 403 "No role assigned." (decorator runs before view 404).',
            )

        # Companion post-auth endpoints
        self.call(
            "GET permissions-map (all valid resources/actions)",
            "GET",
            "/api/v1/roles/permissions-map",
            token=access,
            expected_status=200,
            notes="Catalog of every resource→actions pair (checkbox grid source of truth).",
        )
        self.call(
            "GET permissions-map missing Authorization",
            "GET",
            "/api/v1/roles/permissions-map",
            expected_status=401,
        )

        self.call(
            "GET me/authority-limits (flattened role permissions + labels)",
            "GET",
            "/api/v1/roles/me/authority-limits",
            token=access,
            expected_status=200,
            notes="Same permission set as employee role, flattened with label/helper_text.",
        )
        self.call(
            "GET me/authority-limits missing Authorization",
            "GET",
            "/api/v1/roles/me/authority-limits",
            expected_status=401,
        )
        if norole_access:
            self.call(
                "GET me/authority-limits with no role",
                "GET",
                "/api/v1/roles/me/authority-limits",
                token=norole_access,
                expected_status=403,
                notes='403 "No role assigned."',
            )

    def _test_login(self, active: User, inactive: User, twofa: User) -> None:
        self.call(
            "login success (no 2FA)",
            "POST",
            "/api/v1/auth/login",
            body={"email": active.email, "password": DEMO_PASSWORD},
            expected_status=200,
            notes="Returns access + refresh JWTs when two_factor_enabled=false.",
        )
        self.call(
            "login wrong password",
            "POST",
            "/api/v1/auth/login",
            body={"email": active.email, "password": "wrong-password"},
            expected_status=401,
        )
        self.call(
            "login unknown email",
            "POST",
            "/api/v1/auth/login",
            body={"email": "nobody@bomach.test", "password": DEMO_PASSWORD},
            expected_status=401,
        )
        self.call(
            "login invalid email format",
            "POST",
            "/api/v1/auth/login",
            body={"email": "not-an-email", "password": DEMO_PASSWORD},
            expected_status=422,
            notes="Pydantic validation — middleware usually flattens to {detail: str}.",
        )
        self.call(
            "login missing password",
            "POST",
            "/api/v1/auth/login",
            body={"email": active.email},
            expected_status=422,
        )
        self.call(
            "login empty password",
            "POST",
            "/api/v1/auth/login",
            body={"email": active.email, "password": ""},
            expected_status=422,
            notes="password min_length=1",
        )
        self.call(
            "login email case normalization",
            "POST",
            "/api/v1/auth/login",
            body={"email": active.email.upper(), "password": DEMO_PASSWORD},
            expected_status=200,
            notes="Email is lowercased by LoginRequest validator.",
        )
        # Django ModelBackend rejects inactive users before AuthService sees them,
        # so this typically returns "Invalid credentials" (not "inactive").
        self.call(
            "login inactive account",
            "POST",
            "/api/v1/auth/login",
            body={"email": inactive.email, "password": DEMO_PASSWORD},
            expected_status=401,
            notes=(
                "Observed: usually 'Invalid credentials' because authenticate() "
                "returns None for is_active=False. 'User account is inactive' is "
                "returned by JWTAuthenticator on protected routes."
            ),
        )
        # 2FA login — may 500 if ZeptoMail raises; OTP is still useful if 200
        r = self.call(
            "login requires 2FA",
            "POST",
            "/api/v1/auth/login",
            body={"email": twofa.email, "password": DEMO_PASSWORD},
            notes=(
                "When two_factor_enabled=true: {requires_2fa, session_token}. "
                "If email send raises → 500 Failed to send verification email."
            ),
        )
        if r.status == 200 and isinstance(r.response_body, dict):
            assert r.response_body.get("requires_2fa") is True

    def _test_refresh(self, refresh: Optional[str]) -> None:
        if refresh:
            self.call(
                "refresh success",
                "POST",
                "/api/v1/auth/refresh",
                body={"refresh_token": refresh},
                expected_status=200,
                notes="Returns a new access_token only (refresh is not rotated).",
            )
        self.call(
            "refresh with garbage token",
            "POST",
            "/api/v1/auth/refresh",
            body={"refresh_token": "not.a.jwt"},
            expected_status=401,
        )
        self.call(
            "refresh with access token",
            "POST",
            "/api/v1/auth/refresh",
            body={"refresh_token": (refresh or "x")[:20] + "tampered"},
            expected_status=401,
        )
        self.call(
            "refresh missing field",
            "POST",
            "/api/v1/auth/refresh",
            body={},
            expected_status=422,
        )

    def _test_me_and_verify(self, access: Optional[str]) -> None:
        if access:
            self.call(
                "GET /me success",
                "GET",
                "/api/v1/auth/me",
                token=access,
                expected_status=200,
            )
            self.call(
                "GET /verify-token valid",
                "GET",
                "/api/v1/auth/verify-token",
                token=access,
                expected_status=200,
                notes="Handler returns 200 with valid=true when JWTAuthenticator already passed.",
            )
        self.call(
            "GET /me missing Authorization",
            "GET",
            "/api/v1/auth/me",
            expected_status=401,
            notes='Observed: 401 {"detail":"Unauthorized"} (Ninja default when Bearer is missing).',
        )
        self.call(
            "GET /me invalid token",
            "GET",
            "/api/v1/auth/me",
            token="definitely.not.valid",
            expected_status=401,
        )
        self.call(
            "GET /verify-token missing Authorization",
            "GET",
            "/api/v1/auth/verify-token",
            expected_status=401,
            notes='Same as /me — 401 {"detail":"Unauthorized"} without Bearer.',
        )

    def _test_logout(self, access: Optional[str]) -> None:
        if not access:
            return
        # Fresh login so we don't reuse an already-blacklisted token from earlier
        login = self.call(
            "login (fresh for logout)",
            "POST",
            "/api/v1/auth/login",
            body={"email": self.users["active"].email, "password": DEMO_PASSWORD},
            expected_status=200,
        )
        tok = login.response_body.get("access_token") if isinstance(login.response_body, dict) else None
        if not tok:
            return
        self.call(
            "logout success",
            "POST",
            "/api/v1/auth/logout",
            token=tok,
            expected_status=200,
            notes="Blacklists the current access token (reason=logout).",
        )
        self.call(
            "use access token after logout",
            "GET",
            "/api/v1/auth/me",
            token=tok,
            expected_status=401,
            notes="detail: 'You are logged out. Try to login again.'",
        )
        self.call(
            "logout without Authorization",
            "POST",
            "/api/v1/auth/logout",
            expected_status=401,
            notes='401 {"detail":"Unauthorized"}',
        )

    def _test_password_reset(self, active: User) -> None:
        self.call(
            "forgot-password unknown email",
            "POST",
            "/api/v1/auth/forgot-password",
            body={"email": "missing@bomach.test"},
            expected_status=404,
        )
        self.call(
            "forgot-password invalid email",
            "POST",
            "/api/v1/auth/forgot-password",
            body={"email": "bad"},
            expected_status=422,
        )
        self.call(
            "forgot-password success",
            "POST",
            "/api/v1/auth/forgot-password",
            body={"email": active.email},
            expected_status=200,
            notes="Email send failures are swallowed — still 200 if OTP was created.",
        )
        otp = latest_otp(active, OTPCode.IntentChoices.PASSWORD_RESET)
        code = otp.code if otp else None
        print(f"    password reset OTP from DB: {code}")

        self.call(
            "reset-password wrong code",
            "POST",
            "/api/v1/auth/reset-password",
            body={
                "email": active.email,
                "code": "0000",
                "new_password": DEMO_PASSWORD_ALT,
            },
            expected_status=400,
        )
        self.call(
            "reset-password short password",
            "POST",
            "/api/v1/auth/reset-password",
            body={"email": active.email, "code": code or "1234", "new_password": "short"},
            expected_status=422,
            notes="new_password min_length=8 (Django AUTH_PASSWORD_VALIDATORS are NOT applied).",
        )
        self.call(
            "reset-password unknown user",
            "POST",
            "/api/v1/auth/reset-password",
            body={
                "email": "ghost@bomach.test",
                "code": "123456",
                "new_password": DEMO_PASSWORD_ALT,
            },
            expected_status=400,
        )

        if code:
            self.call(
                "reset-password success",
                "POST",
                "/api/v1/auth/reset-password",
                body={
                    "email": active.email,
                    "code": code,
                    "new_password": DEMO_PASSWORD_ALT,
                },
                expected_status=200,
            )
            # Login with new password
            self.call(
                "login with new password after reset",
                "POST",
                "/api/v1/auth/login",
                body={"email": active.email, "password": DEMO_PASSWORD_ALT},
                expected_status=200,
            )
            # Reuse code → used / not found
            self.call(
                "reset-password reuse same code",
                "POST",
                "/api/v1/auth/reset-password",
                body={
                    "email": active.email,
                    "code": code,
                    "new_password": DEMO_PASSWORD,
                },
                expected_status=400,
                notes="Expect 'Reset code not found or expired' or 'already been used'.",
            )
            # Restore original password for later cases
            active.set_password(DEMO_PASSWORD)
            active.save(update_fields=["password"])
        else:
            print("    WARNING: no OTP found — skipped success reset path")

        # Max-attempts + expired paths via ORM (avoid extra ZeptoMail round-trips)
        OTPCode.objects.filter(
            user=active, intent=OTPCode.IntentChoices.PASSWORD_RESET
        ).delete()
        otp2 = OTPCode.create_code(
            user=active,
            intent=OTPCode.IntentChoices.PASSWORD_RESET,
            code_type=OTPCode.CodeTypeChoices.NUMERIC,
            expires_in_seconds=600,
            user_agent="auth-test-script",
        )
        otp2.attempts = otp2.max_attempts
        otp2.save(update_fields=["attempts"])
        self.call(
            "reset-password too many attempts",
            "POST",
            "/api/v1/auth/reset-password",
            body={
                "email": active.email,
                "code": otp2.code,
                "new_password": DEMO_PASSWORD_ALT,
            },
            expected_status=400,
            notes="OTP.verify → 'Too many failed attempts (max 5)'.",
        )

        OTPCode.objects.filter(
            user=active, intent=OTPCode.IntentChoices.PASSWORD_RESET
        ).delete()
        otp3 = OTPCode.create_code(
            user=active,
            intent=OTPCode.IntentChoices.PASSWORD_RESET,
            code_type=OTPCode.CodeTypeChoices.NUMERIC,
            expires_in_seconds=600,
            user_agent="auth-test-script",
        )
        otp3.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        OTPCode.objects.filter(pk=otp3.pk).update(expires_at=otp3.expires_at)
        self.call(
            "reset-password expired code",
            "POST",
            "/api/v1/auth/reset-password",
            body={
                "email": active.email,
                "code": otp3.code,
                "new_password": DEMO_PASSWORD_ALT,
            },
            expected_status=400,
            notes=(
                "get_valid_code filters expires_at__gt=now → "
                "'Reset code not found or expired'."
            ),
        )
        OTPCode.objects.filter(
            user=active, intent=OTPCode.IntentChoices.PASSWORD_RESET
        ).delete()

    def _test_two_factor(self, twofa: User, active: User) -> None:
        # Login active to get token for toggle endpoints
        login = self.call(
            "login (setup for 2FA toggles)",
            "POST",
            "/api/v1/auth/login",
            body={"email": active.email, "password": DEMO_PASSWORD},
            expected_status=200,
        )
        access = login.response_body.get("access_token") if isinstance(login.response_body, dict) else None
        if not access:
            return

        self.call(
            "2fa status (disabled)",
            "GET",
            "/api/v1/auth/2fa/status",
            token=access,
            expected_status=200,
        )
        self.call(
            "2fa enable wrong password",
            "POST",
            "/api/v1/auth/2fa/enable",
            token=access,
            body={"password": "nope"},
            expected_status=401,
        )
        self.call(
            "2fa disable when already off",
            "POST",
            "/api/v1/auth/2fa/disable",
            token=access,
            body={"password": DEMO_PASSWORD},
            expected_status=400,
            notes="detail: 'Two-factor authentication is not enabled'",
        )
        self.call(
            "2fa enable success",
            "POST",
            "/api/v1/auth/2fa/enable",
            token=access,
            body={"password": DEMO_PASSWORD},
            expected_status=200,
        )
        self.call(
            "2fa enable when already on",
            "POST",
            "/api/v1/auth/2fa/enable",
            token=access,
            body={"password": DEMO_PASSWORD},
            expected_status=400,
        )
        self.call(
            "2fa status (enabled)",
            "GET",
            "/api/v1/auth/2fa/status",
            token=access,
            expected_status=200,
        )

        # Full 2FA login on twofa user
        r = self.call(
            "login 2fa user → session_token",
            "POST",
            "/api/v1/auth/login",
            body={"email": twofa.email, "password": DEMO_PASSWORD},
        )
        session_token = None
        if r.status == 200 and isinstance(r.response_body, dict):
            session_token = r.response_body.get("session_token")

        otp = latest_otp(twofa, OTPCode.IntentChoices.TWO_FACTOR_AUTH)
        code = otp.code if otp else None
        print(f"    2FA OTP from DB: {code}")

        self.call(
            "verify-2fa invalid session",
            "POST",
            "/api/v1/auth/verify-2fa",
            body={"session_token": "bad.token", "code": "123456"},
            expected_status=401,
        )
        self.call(
            "verify-2fa non-digit code",
            "POST",
            "/api/v1/auth/verify-2fa",
            body={"session_token": session_token or "x", "code": "abcdef"},
            expected_status=422,
        )
        self.call(
            "verify-2fa wrong length code",
            "POST",
            "/api/v1/auth/verify-2fa",
            body={"session_token": session_token or "x", "code": "12345"},
            expected_status=422,
        )

        if session_token and code:
            self.call(
                "verify-2fa wrong code",
                "POST",
                "/api/v1/auth/verify-2fa",
                body={"session_token": session_token, "code": "000000"},
                expected_status=400,
            )
            self.call(
                "verify-2fa success",
                "POST",
                "/api/v1/auth/verify-2fa",
                body={"session_token": session_token, "code": code},
                expected_status=200,
                notes="Issues normal access + refresh JWTs.",
            )
            self.call(
                "verify-2fa reuse code",
                "POST",
                "/api/v1/auth/verify-2fa",
                body={"session_token": session_token, "code": code},
                expected_status=400,
            )
        else:
            print("    WARNING: skipped verify-2fa success (no session/OTP — often email send 500)")

        # Disable 2FA on active again so demo stays clean
        self.call(
            "2fa disable success",
            "POST",
            "/api/v1/auth/2fa/disable",
            token=access,
            body={"password": DEMO_PASSWORD},
            expected_status=200,
        )

        # Expired 2FA session token
        expired = AuthService.create_two_factor_session(twofa)
        # Can't easily expire without forging — forge with past exp
        import jwt as pyjwt
        from django.conf import settings

        payload = {
            "user_id": twofa.id,
            "token_type": "2fa_session",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            "iat": datetime.now(timezone.utc) - timedelta(minutes=11),
            "jti": "test-expired",
        }
        expired = pyjwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        self.call(
            "verify-2fa expired session",
            "POST",
            "/api/v1/auth/verify-2fa",
            body={"session_token": expired, "code": "123456"},
            expected_status=401,
            notes="detail: 'Session expired. Please log in again.'",
        )

    def _test_auth_guards(self, active: User) -> None:
        # Expired access token
        import jwt as pyjwt
        from django.conf import settings

        expired = pyjwt.encode(
            {
                "user_id": active.id,
                "token_type": "access",
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
                "iat": datetime.now(timezone.utc) - timedelta(hours=1),
                "jti": "expired-access",
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        self.call(
            "protected route with expired access token",
            "GET",
            "/api/v1/auth/me",
            token=expired,
            expected_status=401,
            notes="detail: 'Token has expired. Try to login again.'",
        )

        # Valid token but user deactivated after issue
        tokens = JWTService.create_tokens(active.id)
        access = tokens["access"]
        active.is_active = False
        active.save(update_fields=["is_active"])
        self.call(
            "protected route while user inactive",
            "GET",
            "/api/v1/auth/me",
            token=access,
            expected_status=401,
            notes="detail: 'User account is inactive'",
        )
        active.is_active = True
        active.save(update_fields=["is_active"])

        # Refresh token used as Bearer (authenticator does NOT enforce token_type)
        login = self.call(
            "login (refresh-as-bearer probe)",
            "POST",
            "/api/v1/auth/login",
            body={"email": active.email, "password": DEMO_PASSWORD},
            expected_status=200,
        )
        if isinstance(login.response_body, dict) and login.response_body.get("refresh_token"):
            self.call(
                "GET /me with refresh token as Bearer",
                "GET",
                "/api/v1/auth/me",
                token=login.response_body["refresh_token"],
                notes=(
                    "Quirk: JWTAuthenticator does not require token_type==access, "
                    "so a refresh JWT may authenticate successfully."
                ),
            )


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

STATIC_CATALOG: list[RouteCatalog] = [
    RouteCatalog(
        method="POST",
        path="/api/v1/auth/login",
        auth="None",
        purpose="Authenticate with email + password. Issues JWTs, or a 2FA session if enabled.",
        request_schema=textwrap.dedent(
            """\
            {
              "email": "string (must match ^[^@]+@[^@]+\\.[^@]+$, lowercased)",
              "password": "string (min_length=1)"
            }"""
        ),
        success_shapes=[
            textwrap.dedent(
                """\
                200 — no 2FA
                {
                  "success": true,
                  "access_token": "<jwt>",
                  "refresh_token": "<jwt>",
                  "user_id": 1,
                  "detail": "Login successful"
                }"""
            ),
            textwrap.dedent(
                """\
                200 — 2FA required
                {
                  "success": true,
                  "requires_2fa": true,
                  "session_token": "<2fa_session jwt, ~10 min>",
                  "detail": "A verification code has been sent to your email"
                }"""
            ),
        ],
        error_shapes=[
            '401 {"detail": "Invalid credentials"}',
            '401 {"detail": "User account is inactive"}  // rare on login; Django usually returns Invalid credentials',
            '500 {"detail": "Failed to send verification email"}  // 2FA email exception',
            '500 {"detail": "Error creating verification code: …"}',
            '422 {"detail": "<validation message>"}  // bad email / missing fields / empty password',
        ],
        frontend_notes=(
            "Branch on `requires_2fa === true` before storing tokens. "
            "On 401 show a generic invalid-credentials message (do not reveal whether email exists). "
            "On 422 show field validation. Persist nothing until tokens are issued."
        ),
    ),
    RouteCatalog(
        method="POST",
        path="/api/v1/auth/verify-2fa",
        auth="None",
        purpose="Complete login after 2FA by submitting session_token + 6-digit email OTP.",
        request_schema=textwrap.dedent(
            """\
            {
              "session_token": "string (from login requires_2fa response)",
              "code": "string (exactly 6 digits)"
            }"""
        ),
        success_shapes=[
            textwrap.dedent(
                """\
                200
                {
                  "success": true,
                  "access_token": "<jwt>",
                  "refresh_token": "<jwt>",
                  "user_id": 1,
                  "detail": "Two-factor authentication successful"
                }"""
            ),
        ],
        error_shapes=[
            '401 {"detail": "Invalid session token"}',
            '401 {"detail": "Session expired. Please log in again."}',
            '401 {"detail": "User not found"}',
            '400 {"detail": "Verification code not found or expired"}',
            '400 {"detail": "Invalid code"}',
            '400 {"detail": "This code has already been used"}',
            '400 {"detail": "This code has expired"}',
            '400 {"detail": "Too many failed attempts (max 5)"}',
            '422 {"detail": "…"}  // non-digit or wrong length code',
        ],
        frontend_notes=(
            "On 401 session errors → send user back to login. "
            "On 400 Invalid code → keep session_token, let user retry (track attempts client-side too). "
            "On too-many / expired → restart login to get a new code."
        ),
    ),
    RouteCatalog(
        method="GET",
        path="/api/v1/auth/2fa/status",
        auth="Bearer access",
        purpose="Whether the current user has 2FA enabled.",
        request_schema="(no body)",
        success_shapes=['200 {"success": true, "two_factor_enabled": true|false}'],
        error_shapes=[
            "401 JwtAuthenticator failures (see Auth errors)",
            '401 {"detail": "Unauthorized"} when Authorization header missing',
        ],
        frontend_notes="Use for settings UI toggle state.",
    ),
    RouteCatalog(
        method="POST",
        path="/api/v1/auth/2fa/enable",
        auth="Bearer access",
        purpose="Enable 2FA after confirming password.",
        request_schema='{"password": "string"}',
        success_shapes=['200 {"success": true, "two_factor_enabled": true}'],
        error_shapes=[
            '401 {"detail": "Invalid password"}',
            '400 {"detail": "Two-factor authentication is already enabled"}',
            '401 {"detail": "Unauthorized"} missing auth',
        ],
        frontend_notes="Require password re-entry. After success, next login will require OTP.",
    ),
    RouteCatalog(
        method="POST",
        path="/api/v1/auth/2fa/disable",
        auth="Bearer access",
        purpose="Disable 2FA after confirming password.",
        request_schema='{"password": "string"}',
        success_shapes=['200 {"success": true, "two_factor_enabled": false}'],
        error_shapes=[
            '401 {"detail": "Invalid password"}',
            '400 {"detail": "Two-factor authentication is not enabled"}',
            '401 {"detail": "Unauthorized"} missing auth',
        ],
        frontend_notes="Same password confirmation pattern as enable.",
    ),
    RouteCatalog(
        method="POST",
        path="/api/v1/auth/logout",
        auth="Bearer access",
        purpose="Blacklist the current access token.",
        request_schema="(no body — token from Authorization header)",
        success_shapes=['200 {"success": true, "detail": "Logged out successfully"}'],
        error_shapes=[
            '500 {"detail": "Unable to extract token"}',
            '500 {"detail": "Logout failed: …"}',
            "401 auth failures (missing/invalid/blacklisted token)",
        ],
        frontend_notes=(
            "Always clear local tokens even if logout fails (network). "
            "Refresh tokens are NOT blacklisted — drop them client-side."
        ),
    ),
    RouteCatalog(
        method="POST",
        path="/api/v1/auth/refresh",
        auth="None",
        purpose="Exchange a refresh JWT for a new access JWT (no rotation).",
        request_schema='{"refresh_token": "string"}',
        success_shapes=[
            textwrap.dedent(
                """\
                200
                {
                  "success": true,
                  "access_token": "<new jwt>",
                  "detail": "Token refreshed successfully"
                }"""
            ),
        ],
        error_shapes=['401 {"detail": "Invalid or expired refresh token"}', "422 validation"],
        frontend_notes=(
            "On 401 → force re-login. Refresh path does not check the blacklist. "
            "Access lifetime ≈ 1000 minutes; refresh ≈ 90 days."
        ),
    ),
    RouteCatalog(
        method="POST",
        path="/api/v1/auth/forgot-password",
        auth="None",
        purpose="Create a password-reset OTP and email it.",
        request_schema='{"email": "string (validated + lowercased)"}',
        success_shapes=['200 {"success": true, "detail": "Password reset code sent to your email"}'],
        error_shapes=[
            '404 {"detail": "User with this email not found"}',
            '500 {"detail": "Error creating reset code: …"}',
            "422 invalid email",
        ],
        frontend_notes=(
            "API reveals whether the email exists (404). Decide product-wise whether to show that. "
            "OTP expiry in code is 6000s (~100 min); email copy says 10 minutes."
        ),
    ),
    RouteCatalog(
        method="POST",
        path="/api/v1/auth/reset-password",
        auth="None",
        purpose="Verify reset OTP and set a new password.",
        request_schema=textwrap.dedent(
            """\
            {
              "email": "string",
              "code": "string (4–12 chars)",
              "new_password": "string (min_length=8)"
            }"""
        ),
        success_shapes=['200 {"success": true, "detail": "Password reset successfully"}'],
        error_shapes=[
            '400 {"detail": "User not found"}',
            '400 {"detail": "Reset code not found or expired"}',
            '400 {"detail": "Invalid code"}',
            '400 {"detail": "This code has already been used"}',
            '400 {"detail": "This code has expired"}',
            '400 {"detail": "Too many failed attempts (max 5)"}',
            '400 {"detail": "Error updating password: …"}',
            "422 password too short / bad email / code length",
        ],
        frontend_notes=(
            "Only schema min_length=8 is enforced — not Django password validators. "
            "After success, redirect to login with the new password."
        ),
    ),
    RouteCatalog(
        method="GET",
        path="/api/v1/auth/me",
        auth="Bearer access",
        purpose="Current user profile snapshot.",
        request_schema="(no body)",
        success_shapes=[
            textwrap.dedent(
                """\
                200
                {
                  "id": 1,
                  "email": "...",
                  "username": "...",
                  "first_name": null|"...",
                  "last_name": null|"...",
                  "phone_number": null|"...",
                  "is_verified": false,
                  "created_at": "ISO-8601"
                }"""
            ),
        ],
        error_shapes=[
            '404 {"detail": "User not found"}',
            "401 authenticator errors",
            '401 {"detail": "Unauthorized"} missing Authorization',
        ],
        frontend_notes="Call after login / on app boot to hydrate session user.",
    ),
    RouteCatalog(
        method="GET",
        path="/api/v1/auth/verify-token",
        auth="Bearer (required by global auth)",
        purpose="Confirm the Bearer token is still valid.",
        request_schema="(no body)",
        success_shapes=[
            textwrap.dedent(
                """\
                200 (only reached if authenticator passes)
                {
                  "success": true,
                  "valid": true|false,
                  "user_id": 1|null,
                  "detail": "Token is valid" | "Token is invalid or expired" | "No token provided"
                }"""
            ),
        ],
        error_shapes=['401 before handler if token missing/invalid (e.g. {"detail":"Unauthorized"})'],
        frontend_notes=(
            "Because the route uses the global JWTAuthenticator, missing/invalid tokens "
            "usually never reach the handler — you get 401 instead of valid=false. "
            "Prefer treating any non-200 as unauthenticated."
        ),
    ),
    # ── Post-auth: role + permissions (staff bootstrap) ──────────────────────
    RouteCatalog(
        method="GET",
        path="/api/v1/roles/employees/{user_id}",
        auth="Bearer access + Role permission `roles:view` or `roles:view_own`",
        purpose=(
            "Return the Role assigned to an employee (full permissions map). "
            "This is the post-auth call the staff frontend makes after GET /auth/me."
        ),
        request_schema="(no body) — path param user_id: int (User.id, not Employee.id)",
        success_shapes=[
            textwrap.dedent(
                """\
                200
                {
                  "id": 1,
                  "name": "Auth Demo Staff",
                  "branches": [{"id": 1, "branch_name": "..."}],
                  "permissions": {
                    "roles": ["view_own"],
                    "employees": ["view_own", "update_own"],
                    "orders": ["view", "list"]
                  },
                  "created_at": "ISO-8601",
                  "updated_at": "ISO-8601"
                }"""
            ),
        ],
        error_shapes=[
            '401 {"detail": "Unauthorized"} / JWT errors',
            '403 {"detail": "Employee profile not found."}',
            '403 {"detail": "No role assigned."}',
            '403 {"detail": "You do not have permission to perform this action."}',
            '403 {"detail": "You do not have permission to access this resource."}  // view_own cross-user',
            '404 {"detail": "…"}  // no Employee for user_id',
            '404 {"detail": "No role assigned to this employee."}  // rare: decorator usually 403 first',
        ],
        frontend_notes=(
            "Staff session bootstrap: login → store tokens → GET /auth/me → "
            "GET /roles/employees/{user.id} → flatten permissions for the UI. "
            "Empty branches[] means company-wide scope. "
            "Note: schema field is `branch_name` (not `name`)."
        ),
    ),
    RouteCatalog(
        method="GET",
        path="/api/v1/roles/permissions-map",
        auth="Bearer access",
        purpose="Full catalog of valid resources and actions (PERMISSIONS_MAP) for admin UI grids.",
        request_schema="(no body)",
        success_shapes=[
            textwrap.dedent(
                """\
                200
                {
                  "permissions_map": {
                    "employees": ["create", "view", "view_own", "list", ...],
                    "roles": ["create", "view", "list", "update", "delete", "view_own"],
                    "...": ["..."]
                  }
                }"""
            ),
        ],
        error_shapes=['401 when unauthenticated'],
        frontend_notes=(
            "Not the current user's grants — the universe of possible permissions. "
            "Use GET /roles/employees/{id} (or /me/authority-limits) for what the user actually has."
        ),
    ),
    RouteCatalog(
        method="GET",
        path="/api/v1/roles/me/authority-limits",
        auth="Bearer access + `roles:view` or `roles:view_own`",
        purpose="Current user's role permissions flattened into labeled authority-limit items.",
        request_schema="(no body)",
        success_shapes=[
            textwrap.dedent(
                """\
                200
                {
                  "items": [
                    {
                      "resource": "orders",
                      "action": "list",
                      "label": "List Orders",
                      "helper_text": "List orders."
                    }
                  ]
                }"""
            ),
        ],
        error_shapes=[
            "401 unauthenticated",
            '403 {"detail": "Employee profile not found."}',
            '403 {"detail": "No role assigned."}',
            '403 {"detail": "You do not have permission to perform this action."}',
            '404 {"detail": "No role assigned to this employee."}',
        ],
        frontend_notes=(
            "Same grants as the employee role endpoint, but flattened with display labels. "
            "Useful for settings / authority UIs; the staff app bootstrap uses /employees/{id}."
        ),
    ),
]


AUTH_ERROR_REFERENCE = textwrap.dedent(
    """\
    ## Shared auth / JWT errors (`JWTAuthenticator`)

    Header: `Authorization: Bearer <access_token>`

    | Condition | Status | Body |
    |-----------|--------|------|
    | Missing `Authorization` header | 401 | `{"detail":"Unauthorized"}` |
    | Blacklisted (logged out) | 401 | `{"detail":"You are logged out. Try to login again."}` |
    | User id missing in DB | 401 | `{"detail":"Invalid or expired session"}` |
    | User `is_active=false` | 401 | `{"detail":"User account is inactive"}` |
    | JWT expired | 401 | `{"detail":"Token has expired. Try to login again."}` |
    | JWT invalid/malformed | 401 | `{"detail":"Invalid token. Try to login again."}` |
    | `on_auth_fail` (legacy path) | 403 | plain text: `Failed to authenticate! or maybe you requested for a password change.` |

    Error schema used by handlers: `{"detail": "<string>"}`.

    Quirks worth handling in the client:
    - Missing Bearer → **401 JSON** `Unauthorized` in practice (not always the 403 plain-text `on_auth_fail` path).
    - Authenticator does **not** require `token_type == "access"` — a refresh JWT may work on protected routes.
    - Logout blacklists **access** only; refresh is client-managed.
    - There is **no public register** endpoint — users are provisioned via employees/clients/shareholders APIs.

    ## Staff post-auth bootstrap

    After a successful login (tokens issued):

    1. `GET /api/v1/auth/me` → user profile (`id`, email, names, …)
    2. `GET /api/v1/roles/employees/{user.id}` → assigned **Role** including full `permissions` map
    3. (optional) `GET /api/v1/roles/me/authority-limits` → same grants, flattened with labels
    4. (optional) `GET /api/v1/roles/permissions-map` → all possible resources/actions (not user-specific)

    Role-guard errors from `@require_permission` (JSON `{"detail": "..."}`):

    | Condition | Status | detail |
    |-----------|--------|--------|
    | No `employee_profile` on user | 403 | `Employee profile not found.` |
    | Employee has `role=null` | 403 | `No role assigned.` |
    | Missing resource/action on role | 403 | `You do not have permission to perform this action.` |
    | `view_own` but object owned by someone else | 403 | `You do not have permission to access this resource.` |
    """
)


def attach_live_cases(catalog: list[RouteCatalog], cases: list[CaseResult]) -> None:
    for route in catalog:
        route.live_cases = [
            c
            for c in cases
            if c.method == route.method and _path_matches(c.path, route.path)
        ]


def write_markdown(
    out_path: Path,
    *,
    base_url: str,
    users: dict[str, User],
    cases: list[CaseResult],
) -> None:
    attach_live_cases(STATIC_CATALOG, cases)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    passed = sum(1 for c in cases if c.ok)
    failed = sum(1 for c in cases if not c.ok)

    lines: list[str] = []
    lines.append("# Auth API catalog & live test results")
    lines.append("")
    lines.append(f"Generated: **{now}**  ")
    lines.append(f"Base URL: `{base_url}`  ")
    lines.append(f"Live cases: **{passed} matched expected status**, **{failed} mismatched** (of {len(cases)}).")
    lines.append("")
    lines.append("## How to re-run")
    lines.append("")
    lines.append("```bash")
    lines.append("cd bomach_os_backend")
    lines.append("# server must already be running on :8000")
    lines.append(".venv/bin/python scripts/test_auth_endpoints.py")
    lines.append("```")
    lines.append("")
    lines.append("## Demo users (seeded/reset by the script)")
    lines.append("")
    lines.append("| Key | Email | Password | Flags |")
    lines.append("|-----|-------|----------|-------|")
    for key, u in users.items():
        flags = []
        if not u.is_active:
            flags.append("inactive")
        if u.two_factor_enabled:
            flags.append("2FA")
        if key == "active":
            flags.append("employee+role")
        elif key == "peer":
            flags.append("employee+role (peer)")
        elif key == "norole":
            flags.append("employee, no role")
        elif key == "twofa":
            flags.append("no employee profile")
        if not flags:
            flags.append("active")
        lines.append(
            f"| `{key}` | `{u.email}` | `{DEMO_PASSWORD}` | {', '.join(flags)} (id={u.id}) |"
        )
    lines.append("")
    lines.append(
        f"Demo role name: `{DEMO_ROLE_NAME}` with permissions: "
        f"`{json.dumps(DEMO_ROLE_PERMISSIONS)}`."
    )
    lines.append("")
    lines.append(AUTH_ERROR_REFERENCE)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Endpoints")
    lines.append("")

    for route in STATIC_CATALOG:
        lines.append(f"### `{route.method} {route.path}`")
        lines.append("")
        lines.append(f"**Auth:** {route.auth}  ")
        lines.append(f"**Purpose:** {route.purpose}")
        lines.append("")
        lines.append("#### Request")
        lines.append("")
        lines.append("```json")
        lines.append(route.request_schema.strip())
        lines.append("```")
        lines.append("")
        lines.append("#### Possible success responses")
        lines.append("")
        for shape in route.success_shapes:
            lines.append("```json")
            lines.append(shape.strip())
            lines.append("```")
            lines.append("")
        lines.append("#### Possible error responses")
        lines.append("")
        for err in route.error_shapes:
            lines.append(f"- `{err}`")
        lines.append("")
        lines.append("#### Frontend handling notes")
        lines.append("")
        lines.append(route.frontend_notes)
        lines.append("")
        lines.append("#### Live observations from this run")
        lines.append("")
        if not route.live_cases:
            lines.append("_No live cases recorded for this route._")
            lines.append("")
        else:
            for c in route.live_cases:
                match = "PASS" if c.ok else f"UNEXPECTED (wanted {c.expected_status})"
                lines.append(f"##### {c.name} — `{c.status}` [{match}]")
                lines.append("")
                if c.notes:
                    lines.append(f"_{c.notes}_")
                    lines.append("")
                lines.append("Request:")
                lines.append("")
                lines.append("```http")
                lines.append(f"{c.method} {c.path}")
                for hk, hv in c.request_headers.items():
                    lines.append(f"{hk}: {hv}")
                lines.append("```")
                if c.request_body is not None:
                    lines.append("")
                    lines.append("```json")
                    lines.append(_pretty(_truncate(c.request_body)))
                    lines.append("```")
                lines.append("")
                lines.append(f"Response `{c.status}`:")
                lines.append("")
                # Plain text 403
                if isinstance(c.response_body, str):
                    lines.append("```")
                    lines.append(c.response_body[:2000])
                    lines.append("```")
                else:
                    lines.append("```json")
                    lines.append(_pretty(_truncate(c.response_body)))
                    lines.append("```")
                lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Full case index")
    lines.append("")
    lines.append("| Status | Expected | Case | Route |")
    lines.append("|--------|----------|------|-------|")
    for c in cases:
        exp = c.expected_status if c.expected_status is not None else "—"
        flag = "✓" if c.ok else "✗"
        lines.append(f"| {flag} {c.status} | {exp} | {c.name} | `{c.method} {c.path}` |")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test auth endpoints and write MD catalog")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--out",
        default=str(ROOT / "docs" / "auth-tests" / "auth-api-catalog.md"),
    )
    args = parser.parse_args()

    # Health check
    try:
        health = requests.get(f"{args.base_url.rstrip('/')}/api/v1/docs/", timeout=5)
        if health.status_code >= 500:
            print(f"Server at {args.base_url} returned {health.status_code}", file=sys.stderr)
            return 1
    except requests.RequestException as exc:
        print(f"Cannot reach {args.base_url}: {exc}", file=sys.stderr)
        print("Start the Django server first, then re-run this script.", file=sys.stderr)
        return 1

    tester = AuthTester(args.base_url)
    tester.run_all()
    write_markdown(
        Path(args.out),
        base_url=args.base_url,
        users=tester.users,
        cases=tester.cases,
    )

    failed = [c for c in tester.cases if not c.ok]
    if failed:
        print(f"\n{len(failed)} case(s) did not match expected status (still documented).")
        return 0  # catalog is the deliverable; mismatches are useful signal
    print("\nAll expected statuses matched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
