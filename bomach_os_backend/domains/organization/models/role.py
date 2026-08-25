from django.core.exceptions import ValidationError
from django.db import models
from django.db.utils import NotSupportedError

from user.models.base import BaseModel

# ── Every resource and its valid actions ────────────────────────────────────
# Format: { "resource_key": ["action", ...] }
# This is the single source of truth. The frontend reads it via the
# GET /roles/permissions-map endpoint to render the checkbox grid.

PERMISSIONS_MAP = {
    # ── User / Core ──
    #   _own variants: every employee can view/update their own profile & docs
    "employees": ["create", "view", "view_own", "list", "update", "update_own", "exit"],
    "employee_documents": [
        "upload",
        "upload_own",
        "view",
        "view_own",
        "list",
        "list_own",
        "delete",
    ],
    "employee_reviews": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "departments": ["create", "list", "update"],
    "department_units": ["create", "list", "update"],
    "roles": ["create", "view", "list", "update", "delete", "view_own"],
    "role_career_paths": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "role_reporting_lines": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "role_kpis": ["create", "view", "view_own", "list", "list_own", "update", "delete"],
    "employee_kpis": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "update_own",
        "delete",
    ],
    "branches": ["create", "view", "list", "update", "set_business_hours"],
    "role_descriptions": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "role_resources": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "role_sops": ["create", "view", "view_own", "list", "list_own", "update", "delete"],
    "role_success_playbook": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "role_target_templates": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "role_training_requirements": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "role_task_templates": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "role_daily_routines": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "employee_targets": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "target_reports": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "approve",
        "reject",
    ],
    "company_settings": ["view", "update"],
    # ── Clients / Leads ──
    "leads": ["create", "view", "list", "update", "delete", "convert_to_client"],
    "clients": ["create", "view", "list", "update"],
    # ── Real Estate ──
    "estates": ["create", "view", "list", "update", "delete"],
    "properties": ["create", "view", "list", "update", "delete"],
    "estate_invoices": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "update_own",
        "delete",
        "submit_for_approval",
        "approve",
        "reject",
        "record_payment",
    ],
    "brokerage": ["create", "view", "list", "update", "delete"],
    "cart": ["view", "add_item", "remove_item", "clear"],
    # ── Partners ──
    "partners": ["create", "view", "list", "update", "delete"],
    "partner_agreements": ["create", "view", "list", "update", "delete"],
    # ── Legal / Compliance ──
    "legal_cases": ["create", "view", "list", "update", "delete", "update_status"],
    "compliance_records": ["create", "view", "list", "update"],
    "compliance_audits": [
        "create",
        "view",
        "list",
        "update",
        "delete",
        "update_status",
        "update_score",
    ],
    "audit_logs": ["list"],
    # ── Corporate ──
    "announcements": ["create", "view", "list", "update", "delete"],
    "board_resolutions": ["create", "view", "list", "update", "delete", "approve"],
    "shareholders": ["create", "view", "list", "update"],
    "meetings": ["create", "view", "list", "update", "delete"],
    "policies": ["create", "view", "list", "update", "delete"],
    "events": ["create", "view", "list", "update", "delete"],
    "loans": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
        "approve",
        "reject",
    ],
    # ── Approvals ──
    "approval_flows": ["create", "view", "list", "update", "delete"],
    "approval_requests": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "approve",
        "reject",
        "cancel",
    ],
    # ── Drawing Bank ──
    "drawings": [
        "create",
        "view",
        "list",
        "update",
        "delete",
        "approve",
        "reject",
        "download",
    ],
    # ── Wallet ──
    "wallet": ["view", "view_own", "list", "list_own", "fund"],
    # ── Client Inventory ──
    "client_inventory": ["create", "view", "list", "update", "delete"],
    # ── Dashboard / Stats ──
    "dashboard": ["view"],
    "stats": ["view"],
    # ── Operations ──
    "projects": ["create", "view", "list", "update", "delete"],
    "tasks": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "update_own",
        "delete",
    ],
    "worksites": ["create", "view", "list", "update", "delete"],
    "contracts": ["create", "view", "list", "update", "delete"],
    "timelines": ["create", "view", "list", "update", "delete"],
    "milestones": ["create", "view", "list", "update", "delete"],
    "site_equipment": ["create", "view", "list", "update", "delete"],
    # ── Services ──
    "categories": ["create", "view", "list", "update", "delete"],
    "content": ["create", "view", "list", "update", "delete"],
    "documents": ["create", "view", "list", "update", "delete"],
    "expenses": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "update_own",
        "delete",
        "approve",
        "reject",
        "pay",
    ],
    "finance_vendors": ["create", "view", "list", "update", "deactivate"],
    "vendor_bills": [
        "create",
        "view",
        "list",
        "update",
        "approve",
        "reject",
        "pay",
        "void",
    ],
    "petty_cash": [
        "create",
        "view",
        "list",
        "update",
        "approve",
        "reject",
        "issue",
        "retire",
        "cancel",
    ],
    "cash_flow": ["view"],
    "chart_of_accounts": ["create", "view", "list", "update", "deactivate"],
    "journals": ["create", "view", "list", "update", "post", "reverse"],
    "general_ledger": ["view", "list"],
    "finance_settings": ["view", "update"],
    "financial_reports": ["view", "export"],
    "finance_audit": ["view", "export"],
    "bank_reconciliation": [
        "create",
        "view",
        "list",
        "update",
        "match",
        "reconcile",
        "close",
    ],
    "fixed_asset_categories": ["create", "view", "list", "update", "deactivate"],
    "fixed_assets": [
        "create",
        "view",
        "list",
        "update",
        "capitalize",
        "depreciate",
        "dispose",
    ],
    "finance_payroll": [
        "list",
        "view",
        "create",
        "update",
        "calculate",
        "submit",
        "approve",
        "reject",
        "pay",
        "cancel",
    ],
    "commissions": [
        "list",
        "view",
        "create",
        "update",
        "calculate",
        "approve",
        "reject",
    ],
    "statutory": [
        "list",
        "view",
        "create",
        "update",
        "generate",
        "submit",
        "approve",
        "reject",
        "pay",
        "void",
    ],
    "service_invoices": ["create", "view", "list", "update", "delete"],
    "service_leads": ["create", "view", "list", "update", "delete"],
    "marketing_campaigns": ["create", "view", "list", "update", "delete"],
    "orders": ["create", "view", "list", "update", "delete"],
    "payments": ["create", "view", "list", "delete"],
    "quotes": ["create", "view", "list", "update", "delete", "approve"],
    "service_requests": ["create", "view", "list", "update", "delete"],
    "services": ["create", "view", "list", "update", "delete"],
    "service_subservices": ["create", "view", "list", "update", "delete"],
    "service_request_forms": ["create", "view", "list", "update", "delete"],
    "service_pricing_configs": ["create", "view", "list", "update", "delete"],
    "service_branch_activations": ["create", "view", "list", "update", "delete"],
    "service_workflows": ["create", "view", "list", "update", "delete"],
    "feedback": ["create", "view", "list", "update", "delete"],
    "reports": ["view"],
    # ── HR ──
    "job_postings": ["create", "view", "list", "update", "delete", "update_status"],
    "applicants": ["create", "view", "list", "update", "delete", "update_status"],
    "interviews": ["create", "view", "list", "update", "delete", "submit_feedback"],
    "offer_letters": ["create", "view", "list", "update"],
    "leave_requests": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "update_own",
        "delete",
        "delete_own",
        "approve",
        "reject",
    ],
    "payroll": ["list", "list_own", "process_batch", "make_payment", "authorize"],
    "performance_reviews": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "training_programs": ["create", "view", "list", "update", "delete"],
    "assets": ["create", "view", "view_own", "list", "list_own", "update", "delete"],
    "awards": ["create", "view", "view_own", "list", "list_own", "update", "delete"],
    "work_reports": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "update_own",
        "delete",
        "approve",
        "reject",
    ],
    "disciplinary_cases": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "monthly_scorecards": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "employee_evaluations": [
        "create",
        "view",
        "view_own",
        "list",
        "list_own",
        "update",
        "delete",
    ],
    "kpis": ["create", "view", "view_own", "list", "list_own", "update", "delete"],
    # ── CRM / Sales Pipeline ──
    "funnel": ["view"],
    "marketing_dashboard": ["view"],
    "inquiries": ["create", "view", "list", "update", "assign"],
    "followups": ["create", "view", "list", "update"],
    "deals": ["create", "view", "list", "update", "delete"],
    "pipeline": ["view"],
    "revenue_execution": ["create", "view", "list", "update", "delete", "complete"],
    # ── Biometric / Attendance ──
    #   work_locations: employee-facing actions (submit a location proposal,
    #   view/list own or all locations, delete own pending proposal).
    #   work_location_approvals: admin-facing actions (review pending proposals,
    #   approve/reject, directly whitelist, edit radius, override attendance).
    "work_locations": ["submit", "view", "view_own", "list", "list_own", "delete_own"],
    "work_location_approvals": [
        "create",
        "list_pending",
        "approve",
        "reject",
        "manage",
        "override",
        "force_delete",
    ],
    "attendance": ["view", "list", "view_own", "list_own"],
    # ── Notifications ──
    "notifications": ["view", "list", "mark_read", "mark_all_read"],
    # ── Command Center ──
    "command_center": ["view"],
    # ── Workflow Rules ──
    "workflow_rules": ["create", "view", "list", "update", "delete"],
}


PERMISSION_HELPERS = {
    "employees.create": {
        "label": "Create Employees",
        "helper_text": "Create employee records.",
    },
    "employees.view": {
        "label": "View Employees",
        "helper_text": "View employee profiles.",
    },
    "employees.view_own": {
        "label": "View Own Employee Profile",
        "helper_text": "View the signed-in employee profile.",
    },
    "employees.list": {
        "label": "List Employees",
        "helper_text": "List employee records.",
    },
    "employees.update": {
        "label": "Update Employees",
        "helper_text": "Update employee profiles.",
    },
    "employees.update_own": {
        "label": "Update Own Employee Profile",
        "helper_text": "Update the signed-in employee profile.",
    },
    "employees.exit": {
        "label": "Exit Employees",
        "helper_text": "Process employee exits.",
    },
    "leave_requests.approve": {
        "label": "Approve Leave Requests",
        "helper_text": "Approve leave requests.",
    },
    "leave_requests.reject": {
        "label": "Reject Leave Requests",
        "helper_text": "Reject leave requests.",
    },
    "approval_requests.approve": {
        "label": "Approve Approval Requests",
        "helper_text": "Approve submitted approval requests.",
    },
    "approval_requests.reject": {
        "label": "Reject Approval Requests",
        "helper_text": "Reject submitted approval requests.",
    },
    "loans.approve": {
        "label": "Approve Loans",
        "helper_text": "Approve employee loan requests.",
    },
    "loans.reject": {
        "label": "Reject Loans",
        "helper_text": "Reject employee loan requests.",
    },
    "board_resolutions.approve": {
        "label": "Approve Board Resolutions",
        "helper_text": "Approve board resolutions.",
    },
    "expenses.approve": {
        "label": "Approve Expenses",
        "helper_text": "Approve submitted expense records.",
    },
    "expenses.reject": {
        "label": "Reject Expenses",
        "helper_text": "Reject submitted expense records.",
    },
    "estate_invoices.approve": {
        "label": "Approve Estate Invoices",
        "helper_text": "Approve estate invoices.",
    },
    "estate_invoices.reject": {
        "label": "Reject Estate Invoices",
        "helper_text": "Reject estate invoices.",
    },
    "work_location_approvals.approve": {
        "label": "Approve Work Locations",
        "helper_text": "Approve proposed work locations.",
    },
    "work_location_approvals.reject": {
        "label": "Reject Work Locations",
        "helper_text": "Reject proposed work locations.",
    },
    "target_reports.approve": {
        "label": "Approve Target Reports",
        "helper_text": "Approve submitted employee target progress reports.",
    },
    "target_reports.reject": {
        "label": "Reject Target Reports",
        "helper_text": "Reject submitted employee target progress reports.",
    },
    "work_reports.approve": {
        "label": "Approve Work Reports",
        "helper_text": "Approve submitted employee work reports.",
    },
    "work_reports.reject": {
        "label": "Reject Work Reports",
        "helper_text": "Reject submitted employee work reports.",
    },
}


def _validate_permissions(value):
    """Validate that permissions dict only contains known resources and actions."""
    if not isinstance(value, dict):
        raise ValidationError("Permissions must be a JSON object.")
    for resource, actions in value.items():
        if resource not in PERMISSIONS_MAP:
            raise ValidationError(
                f"Unknown resource '{resource}'. "
                f"Valid resources: {', '.join(sorted(PERMISSIONS_MAP.keys()))}"
            )
        if not isinstance(actions, list):
            raise ValidationError(f"Actions for '{resource}' must be a list.")
        valid_actions = set(PERMISSIONS_MAP[resource])
        for action in actions:
            if action not in valid_actions:
                raise ValidationError(
                    f"Unknown action '{action}' for '{resource}'. "
                    f"Valid: {', '.join(sorted(valid_actions))}"
                )


def get_permission_helper(resource: str, action: str) -> dict:
    key = f"{resource}.{action}"
    helper = PERMISSION_HELPERS.get(key)
    if helper:
        return helper

    resource_label = resource.replace("_", " ").title()
    action_label = action.replace("_", " ").title()
    return {
        "label": f"{action_label} {resource_label}",
        "helper_text": f"{action_label} {resource.replace('_', ' ')}.",
    }


class Role(BaseModel):
    """
    A named set of permissions with branch-based scoping.

    `permissions` is a JSON dict of ``{ "resource": ["action", ...] }``.
    Only resources/actions listed in PERMISSIONS_MAP are accepted.

    `branches` defines which branches this role grants access to.
    If no branches are set, the role is company-wide (access to all branches).

    Roles are directly assigned to employees via Employee.role FK.
    """

    name = models.CharField(max_length=100, unique=True)

    branches = models.ManyToManyField(
        "Branch",
        blank=True,
        related_name="roles",
        help_text="Branches this role grants access to. Empty = company-wide.",
    )

    permissions = models.JSONField(
        default=dict,
        blank=True,
        validators=[_validate_permissions],
        help_text='{"resource": ["action", ...]}',
    )

    class Meta:
        app_label = "user"
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        _validate_permissions(self.permissions)

    def has_permission(self, resource: str, action: str) -> bool:
        """Check if this role grants a specific permission."""
        return action in self.permissions.get(resource, [])

    @property
    def is_company_wide(self) -> bool:
        """True if this role has no branch restrictions (company-wide access)."""
        return not self.branches.exists()

    def get_branch_ids(self) -> list:
        """Return the list of branch IDs this role is scoped to."""
        return list(self.branches.values_list("id", flat=True))

    @staticmethod
    def employee_has_permission(employee, resource: str, action: str) -> bool:
        """Check if an employee has a permission through their assigned role.

        Uses DB-level __contains on PostgreSQL, falls back to Python
        filtering on SQLite.
        """
        role = getattr(employee, "role", None)
        if role is None:
            return False
        try:
            return Role.objects.filter(
                pk=role.pk,
                permissions__contains={resource: [action]},
            ).exists()
        except NotSupportedError:
            # SQLite fallback: check in Python
            return action in role.permissions.get(resource, [])
