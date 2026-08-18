"""
Management command to test ALL permission-protected endpoints.

Creates employees at different levels, assigns roles with specific permissions,
then hits every endpoint and records pass/fail results.

Usage:
    python manage.py test_permissions
"""
import json
import uuid
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth.hashers import make_password

from user.models.user import User
from user.models.employee import Employee
from user.models.roles import Department, Unit
from user.models.role import Role
from user.models.branch import Branch
from user.services.jwt_service import JWTService


# ── Endpoint registry ─────────────────────────────────────────────────────────
# Each entry: (method, url, description, body_or_none, requires_id)
# We use Django's test client to hit these via the full URL.

ENDPOINTS = [
    # ── Roles ──
    ("GET",  "/api/v1/roles/",               "roles:list",           None),
    ("GET",  "/api/v1/roles/permissions-map", "roles:permissions-map", None),
    ("POST", "/api/v1/roles/",               "roles:create",
     {"name": f"TestRole-{uuid.uuid4().hex[:6]}", "permissions": {"employees": ["list"]}}),
    # roles:view, update, delete tested with created role id below

    # ── Employees ──
    ("GET",  "/api/v1/employees/employees",  "employees:list",       None),
    ("GET",  "/api/v1/employees/department", "departments:list",     None),
    ("GET",  "/api/v1/employees/unit",       "department_units:list", None),

    # ── Branches ──
    ("GET",  "/api/v1/branch/",              "branches:list",        None),

    # ── Company ──
    ("GET",  "/api/v1/company/",             "company:view",         None),

    # ── Clients / Leads ──
    ("GET",  "/api/v1/clients/leads/",       "leads:list",           None),
    ("GET",  "/api/v1/clients/clients/",     "clients:list",         None),

    # ── Estates ──
    ("GET",  "/api/v1/estates/",             "estates:list",         None),
    ("GET",  "/api/v1/estates/properties/",  "properties:list",      None),

    # ── Estate Invoices ──
    ("GET",  "/api/v1/estate-invoices/",     "estate_invoices:list", None),

    # ── Partners ──
    ("GET",  "/api/v1/partners/",            "partners:list",        None),

    # ── Legal / Compliance ──
    ("GET",  "/api/v1/cases/",               "legal_cases:list",     None),
    ("GET",  "/api/v1/compliance/",          "compliance_records:list", None),
    ("GET",  "/api/v1/audits/",              "compliance_audits:list", None),
    ("GET",  "/api/v1/audit-logs/",          "audit_logs:list",      None),

    # ── Corporate ──
    ("GET",  "/api/v1/announcements/",       "announcements:list",   None),
    ("GET",  "/api/v1/board-resolutions/",   "board_resolutions:list", None),
    ("GET",  "/api/v1/shareholders/",        "shareholders:list",    None),
    ("GET",  "/api/v1/meetings/",            "meetings:list",        None),
    ("GET",  "/api/v1/policies/",            "policies:list",        None),
    ("GET",  "/api/v1/events/",              "events:list",          None),

    # ── Loans ──
    ("GET",  "/api/v1/loans",                "loans:list",           None),

    # ── Approvals ──
    ("GET",  "/api/v1/approvals/flows",      "approval_flows:list",  None),
    ("GET",  "/api/v1/approvals/requests",   "approval_requests:list", None),

    # ── Drawing Bank ──
    ("GET",  "/api/v1/drawing-bank/",        "drawings:list",        None),

    # ── Wallet ──
    ("GET",  "/api/v1/wallet/transactions/", "wallet:list",          None),

    # ── Client Inventory ──
    ("GET",  "/api/v1/inventory/",           "client_inventory:list", None),

    # ── HR ──
    ("GET",  "/api/v1/job-postings",         "job_postings:list",    None),
    ("GET",  "/api/v1/leave-requests",       "leave_requests:list",  None),
    ("GET",  "/api/v1/payroll",              "payroll:list",         None),
    ("GET",  "/api/v1/assets",               "assets:list",          None),
    ("GET",  "/api/v1/awards",               "awards:list",          None),

    # ── Expenses ──
    ("GET",  "/api/v1/expenses",             "expenses:list",        None),
]


class Command(BaseCommand):
    help = "Test all permission-protected endpoints with different employee levels"

    def handle(self, *args, **options):
        # Allow testserver host for Django test client
        from django.conf import settings
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("  PERMISSION ENDPOINT TEST SUITE")
        self.stdout.write("=" * 80 + "\n")

        # 1. Create test infrastructure
        self.stdout.write("Setting up test data...")
        test_data = self._create_test_data()
        self.stdout.write(self.style.SUCCESS("  Test data created.\n"))

        # 2. Run tests for each employee level
        all_results = {}
        for level_key, info in test_data["employees"].items():
            user = info["user"]
            token = JWTService.create_tokens(user.id)["access"]
            results = self._test_endpoints(level_key, token, info)
            all_results[level_key] = results

        # 3. Write results
        self._write_results(all_results, test_data)

        # 4. Cleanup
        self._cleanup(test_data)

        self.stdout.write(self.style.SUCCESS(
            f"\nResults written to: test_permission_results.md"
        ))

    def _create_test_data(self):
        """Create employees at various levels with appropriate roles."""
        branch = Branch(
            branch_name=f"TestBranch-{uuid.uuid4().hex[:6]}",
            country="TestCountry",
            country_code="TST",
            state="TestState",
            office_address="123 Test St",
            contact_email="test@test.com",
            contact_phone="+2348012345678",
        )
        branch.save()

        branch2 = Branch(
            branch_name=f"TestBranch2-{uuid.uuid4().hex[:6]}",
            country="TestCountry",
            country_code="TST",
            state="TestState",
            office_address="456 Test Ave",
            contact_email="test2@test.com",
            contact_phone="+2348012345679",
        )
        branch2.save()

        # Department + Unit
        dept, _ = Department.objects.get_or_create(name="operations")
        unit, _ = Unit.objects.get_or_create(name=f"TestUnit-{uuid.uuid4().hex[:6]}", department=dept)

        # ── Roles ──
        # CEO role: full access to everything
        ceo_perms = {}
        from user.models.role import PERMISSIONS_MAP
        for resource, actions in PERMISSIONS_MAP.items():
            # Give all non-_own actions
            ceo_perms[resource] = [a for a in actions if not a.endswith("_own")]
        ceo_role = Role.objects.create(
            name=f"CEO-Full-{uuid.uuid4().hex[:6]}",
            permissions=ceo_perms,
        )

        # Manager role: broad access, scoped to branch
        manager_perms = {
            "employees": ["create", "view", "list", "update", "exit"],
            "employee_documents": ["upload", "view", "list", "delete"],
            "employee_reviews": ["create", "view", "list", "update", "delete"],
            "departments": ["list"],
            "department_units": ["list"],
            "roles": ["view", "list"],
            "branches": ["view", "list"],
            "company_settings": ["view"],
            "leads": ["create", "view", "list", "update", "delete", "convert_to_client"],
            "clients": ["create", "view", "list", "update"],
            "estates": ["create", "view", "list", "update", "delete"],
            "properties": ["create", "view", "list", "update", "delete"],
            "estate_invoices": ["create", "view", "list", "update", "delete",
                                "submit_for_approval", "approve", "record_payment"],
            "partners": ["view", "list"],
            "legal_cases": ["create", "view", "list", "update"],
            "compliance_records": ["create", "view", "list", "update"],
            "compliance_audits": ["create", "view", "list", "update"],
            "audit_logs": ["list"],
            "announcements": ["create", "view", "list", "update", "delete"],
            "board_resolutions": ["view", "list"],
            "shareholders": ["view", "list"],
            "meetings": ["create", "view", "list", "update", "delete"],
            "policies": ["view", "list"],
            "events": ["create", "view", "list", "update", "delete"],
            "loans": ["view", "list", "approve", "reject"],
            "approval_flows": ["view", "list"],
            "approval_requests": ["create", "view", "list", "approve", "reject"],
            "drawings": ["create", "view", "list", "update", "approve", "reject", "download"],
            "wallet": ["view", "list"],
            "client_inventory": ["create", "view", "list", "update", "delete"],
            "job_postings": ["create", "view", "list", "update"],
            "leave_requests": ["view", "list", "approve", "reject"],
            "payroll": ["list"],
            "assets": ["create", "view", "list", "update", "delete"],
            "awards": ["create", "view", "list", "update", "delete"],
            "expenses": ["view", "list", "approve", "reject"],
        }
        manager_role = Role.objects.create(
            name=f"Manager-{uuid.uuid4().hex[:6]}",
            permissions=manager_perms,
        )

        # Head of Operations role
        head_perms = {
            "employees": ["view", "list", "update"],
            "employee_documents": ["view", "list"],
            "departments": ["list"],
            "department_units": ["list"],
            "roles": ["view", "list"],
            "branches": ["view", "list"],
            "company_settings": ["view"],
            "leads": ["view", "list"],
            "clients": ["view", "list"],
            "estates": ["view", "list"],
            "properties": ["view", "list"],
            "estate_invoices": ["view", "list"],
            "partners": ["view", "list"],
            "legal_cases": ["view", "list"],
            "compliance_records": ["view", "list"],
            "compliance_audits": ["view", "list"],
            "audit_logs": ["list"],
            "announcements": ["view", "list"],
            "board_resolutions": ["view", "list"],
            "shareholders": ["view", "list"],
            "meetings": ["view", "list"],
            "policies": ["view", "list"],
            "events": ["view", "list"],
            "loans": ["view", "list"],
            "approval_flows": ["view", "list"],
            "approval_requests": ["view", "list"],
            "drawings": ["view", "list"],
            "wallet": ["view", "list"],
            "client_inventory": ["view", "list"],
            "job_postings": ["view", "list"],
            "leave_requests": ["view", "list"],
            "payroll": ["list"],
            "assets": ["view", "list"],
            "awards": ["view", "list"],
            "expenses": ["view", "list"],
        }
        head_role = Role.objects.create(
            name=f"HeadOps-{uuid.uuid4().hex[:6]}",
            permissions=head_perms,
        )

        # Junior role: very limited, only _own access
        junior_perms = {
            "employees": ["view_own"],
            "employee_documents": ["upload_own", "view_own", "list_own"],
            "loans": ["create", "view_own", "list_own"],
            "leave_requests": ["create", "view_own", "list_own"],
            "events": ["list"],
            "announcements": ["list"],
            "policies": ["list"],
        }
        junior_role = Role.objects.create(
            name=f"Junior-{uuid.uuid4().hex[:6]}",
            permissions=junior_perms,
        )

        # Intern role: minimal access
        intern_perms = {
            "employees": ["view_own"],
            "events": ["list"],
            "announcements": ["list"],
            "policies": ["list"],
        }
        intern_role = Role.objects.create(
            name=f"Intern-{uuid.uuid4().hex[:6]}",
            permissions=intern_perms,
        )

        # ── Employees ──
        # Assign roles to branches
        manager_role.branches.add(branch)
        head_role.branches.add(branch)
        junior_role.branches.add(branch)
        intern_role.branches.add(branch)

        employees = {}
        test_configs = {
            "ceo":             {"role": ceo_role,     "branch": branch,  "dept": dept},
            "manager":         {"role": manager_role, "branch": branch,  "dept": dept},
            "manager_branch2": {"role": manager_role, "branch": branch2, "dept": dept},
            "head_operations": {"role": head_role,    "branch": branch,  "dept": dept},
            "junior":          {"role": junior_role,  "branch": branch,  "dept": dept},
            "intern":          {"role": intern_role,  "branch": branch,  "dept": dept},
        }

        for key, config in test_configs.items():
            uid = uuid.uuid4().hex[:8]
            user = User.objects.create(
                username=f"test_{key}_{uid}",
                email=f"test_{key}_{uid}@test.com",
                password=make_password("testpass123"),
                first_name=f"Test",
                last_name=key.replace("_", " ").title(),
                is_active=True,
            )
            emp = Employee.objects.create(
                employee_id=f"TEST-{uid}",
                user=user,
                branch=config["branch"],
                department=config["dept"],
                role=config["role"],
                employment_status="active",
                is_active=True,
            )
            emp.department_units.add(unit)
            employees[key] = {"user": user, "employee": emp, "role_name": config["role"].name}

        return {
            "employees": employees,
            "roles": [ceo_role, manager_role, head_role, junior_role, intern_role],
            "branch": branch,
            "branch2": branch2,
            "dept": dept,
            "unit": unit,
        }

    def _test_endpoints(self, level_key, token, info):
        """Test all endpoints for a given employee."""
        from django.test import Client as TestClient
        client = TestClient()
        results = []

        self.stdout.write(f"\nTesting as: {level_key} (level={info['role_name']})")
        self.stdout.write("-" * 60)

        for entry in ENDPOINTS:
            method, url, desc, body = entry[0], entry[1], entry[2], entry[3]

            try:
                headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
                if method == "GET":
                    resp = client.get(url, **headers)
                elif method == "POST":
                    resp = client.post(
                        url,
                        data=json.dumps(body) if body else "{}",
                        content_type="application/json",
                        **headers,
                    )
                elif method == "PUT":
                    resp = client.put(
                        url,
                        data=json.dumps(body) if body else "{}",
                        content_type="application/json",
                        **headers,
                    )
                elif method == "DELETE":
                    resp = client.delete(url, **headers)
                else:
                    results.append((desc, "SKIP", "Unknown method"))
                    continue

                status = resp.status_code
                # Determine result
                if status == 403:
                    result = "DENIED"
                    detail = self._get_detail(resp)
                elif status in (200, 201, 204):
                    result = "PASS"
                    detail = f"HTTP {status}"
                elif status == 401:
                    result = "AUTH_FAIL"
                    detail = self._get_detail(resp)
                elif status == 404:
                    # 404 on list endpoints = problem, on detail endpoints = expected
                    result = "PASS (404)"
                    detail = "Not found (may be expected)"
                elif status == 422:
                    result = "PASS (422)"
                    detail = "Validation error (endpoint reached)"
                else:
                    result = f"HTTP_{status}"
                    detail = self._get_detail(resp)

                icon = {
                    "PASS": self.style.SUCCESS("PASS"),
                    "PASS (404)": self.style.WARNING("PASS(404)"),
                    "PASS (422)": self.style.WARNING("PASS(422)"),
                    "DENIED": self.style.ERROR("DENIED"),
                    "AUTH_FAIL": self.style.ERROR("AUTH_FAIL"),
                }.get(result, self.style.WARNING(result))

                self.stdout.write(f"  {icon:20s} {method:6s} {desc:40s} {detail}")
                results.append((desc, result, detail))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ERROR    {method:6s} {desc:40s} {str(e)[:60]}"))
                results.append((desc, "ERROR", str(e)[:100]))

        return results

    def _get_detail(self, resp):
        """Extract error detail from response."""
        try:
            data = json.loads(resp.content)
            if isinstance(data, dict):
                return data.get("detail", "")[:80]
            return str(data)[:80]
        except Exception:
            return resp.content[:80].decode("utf-8", errors="replace")

    def _write_results(self, all_results, test_data):
        """Write results to a markdown file."""
        lines = []
        lines.append("# Permission Endpoint Test Results")
        lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Summary table
        lines.append("## Summary\n")
        lines.append("| Employee Level | PASS | DENIED | ERROR/OTHER | Total |")
        lines.append("|---|---|---|---|---|")

        for level_key, results in all_results.items():
            info = test_data["employees"][level_key]
            pass_count = sum(1 for _, r, _ in results if r.startswith("PASS"))
            denied_count = sum(1 for _, r, _ in results if r == "DENIED")
            other_count = len(results) - pass_count - denied_count
            lines.append(
                f"| {level_key} ({info['role_name']}) "
                f"| {pass_count} | {denied_count} | {other_count} | {len(results)} |"
            )

        # Detailed results per level
        for level_key, results in all_results.items():
            info = test_data["employees"][level_key]
            lines.append(f"\n## {level_key} (level: {info['role_name']})\n")

            # Passing
            passing = [(d, r, det) for d, r, det in results if r.startswith("PASS")]
            if passing:
                lines.append("### Passing\n")
                lines.append("| Endpoint | Status | Detail |")
                lines.append("|---|---|---|")
                for desc, result, detail in passing:
                    lines.append(f"| {desc} | {result} | {detail} |")

            # Denied
            denied = [(d, r, det) for d, r, det in results if r == "DENIED"]
            if denied:
                lines.append("\n### Denied (403)\n")
                lines.append("| Endpoint | Detail |")
                lines.append("|---|---|")
                for desc, result, detail in denied:
                    lines.append(f"| {desc} | {detail} |")

            # Errors/Other
            other = [(d, r, det) for d, r, det in results
                     if not r.startswith("PASS") and r != "DENIED"]
            if other:
                lines.append("\n### Errors / Other\n")
                lines.append("| Endpoint | Status | Detail |")
                lines.append("|---|---|---|")
                for desc, result, detail in other:
                    lines.append(f"| {desc} | {result} | {detail} |")

        # Cross-reference: which endpoints are denied for which levels
        lines.append("\n## Cross-Reference: Endpoint x Level\n")
        level_keys = list(all_results.keys())
        header = "| Endpoint | " + " | ".join(level_keys) + " |"
        sep = "|---|" + "|".join(["---"] * len(level_keys)) + "|"
        lines.append(header)
        lines.append(sep)

        # Get all endpoint descriptions
        all_descs = []
        for entry in ENDPOINTS:
            all_descs.append(entry[2])

        for desc in all_descs:
            row = f"| {desc} |"
            for lk in level_keys:
                result_for_ep = next(
                    (r for d, r, _ in all_results[lk] if d == desc), "N/A"
                )
                if result_for_ep.startswith("PASS"):
                    row += " PASS |"
                elif result_for_ep == "DENIED":
                    row += " DENIED |"
                else:
                    row += f" {result_for_ep} |"
            lines.append(row)

        output_path = "test_permission_results.md"
        with open(output_path, "w") as f:
            f.write("\n".join(lines))

    def _cleanup(self, test_data):
        """Remove test data."""
        self.stdout.write("\nCleaning up test data...")
        for role in test_data["roles"]:
            role.delete()
        for key, info in test_data["employees"].items():
            info["employee"].delete()
            info["user"].delete()
        test_data["unit"].delete()
        test_data["branch"].delete()
        test_data["branch2"].delete()
        self.stdout.write(self.style.SUCCESS("  Cleanup complete."))
