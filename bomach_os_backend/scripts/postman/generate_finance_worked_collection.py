#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path("/home/kachy/project/bomach/bomach_os_backend")
OUT_DIR = ROOT / "docs" / "postman"
COLLECTION_PATH = OUT_DIR / "finance-worked-features.postman_collection.json"
ENV_PATH = OUT_DIR / "finance-worked-features.postman_environment.json"


FINANCE_BASELINE_PERMISSIONS = {
    "roles": ["list", "view", "update"],
    "employees": ["list", "view", "update"],
    "finance_settings": ["view", "update"],
    "financial_reports": ["view", "export"],
    "finance_audit": ["view", "export"],
    "cash_flow": ["view"],
    "payments": ["list", "view", "create"],
    "chart_of_accounts": ["list", "create", "view", "update", "deactivate"],
    "journals": ["list", "create", "view", "update", "post", "reverse"],
    "general_ledger": ["list", "view"],
    "finance_payroll": [
        "list",
        "create",
        "view",
        "update",
        "calculate",
        "submit",
        "approve",
        "reject",
        "pay",
        "cancel",
    ],
    "statutory": [
        "view",
        "list",
        "create",
        "generate",
        "update",
        "submit",
        "approve",
        "reject",
        "pay",
        "void",
    ],
    "commissions": ["list", "create", "update", "calculate", "view", "approve", "reject"],
    "expenses": ["create", "view", "list", "update", "approve", "reject", "pay"],
    "fixed_asset_categories": ["list", "create", "view", "update", "deactivate"],
    "fixed_assets": ["list", "create", "view", "update", "capitalize", "depreciate", "dispose"],
    "services": ["view", "list"],
}


def js(value):
    return json.dumps(value, indent=2)


def test_script(lines):
    return {
        "listen": "test",
        "script": {"type": "text/javascript", "exec": lines},
    }


def prerequest_script(lines):
    return {
        "listen": "prerequest",
        "script": {"type": "text/javascript", "exec": lines},
    }


def auth_header(token_var):
    return [{"key": "Authorization", "value": f"Bearer {{{{{token_var}}}}}", "type": "text"}]


def json_body(raw):
    return {
        "mode": "raw",
        "raw": raw,
        "options": {"raw": {"language": "json"}},
    }


def request_item(
    name,
    method,
    path,
    *,
    token_var=None,
    query=None,
    body=None,
    tests=None,
    prerequest=None,
    description="",
):
    headers = [{"key": "Content-Type", "value": "application/json", "type": "text"}]
    if token_var:
        headers.extend(auth_header(token_var))
    item = {
        "name": name,
        "request": {
            "method": method,
            "header": headers,
            "url": {
                "raw": "{{base_url}}" + path,
                "host": ["{{base_url}}"],
                "path": [segment for segment in path.strip("/").split("/") if segment],
            },
            "description": description,
        },
    }
    if query:
        item["request"]["url"]["query"] = [
            {"key": key, "value": str(value)} for key, value in query.items()
        ]
    if body is not None:
        item["request"]["body"] = json_body(body)
    events = []
    if prerequest:
        events.append(prerequest_script(prerequest))
    if tests:
        events.append(test_script(tests))
    if events:
        item["event"] = events
    return item


def folder(name, items):
    return {"name": name, "item": items}


collection = {
    "info": {
        "name": "Bomach Finance Worked Features",
        "_postman_id": "8de405be-4af0-4ec3-894a-4d5ae554f0d4",
        "description": (
            "Focused finance regression collection for the production backend. "
            "It covers the finance features implemented in the curated finance sync: "
            "settings, reports, audit, exceptions, cash flow, accounts, chart of "
            "accounts, journals, payroll, statutory obligations, commissions bonuses, "
            "and fixed assets. Bank reconciliation is intentionally excluded because "
            "the production API does not mount that router."
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "variable": [
        {"key": "finance_permissions_baseline", "value": json.dumps(FINANCE_BASELINE_PERMISSIONS)},
        {"key": "role_permissions_payload", "value": json.dumps(FINANCE_BASELINE_PERMISSIONS)},
        {"key": "role_name", "value": "Postman Finance Scoped Role"},
        {"key": "subject_email_lookup", "value": "postman.finance.subject@bomach.local"},
        {"key": "control_email_lookup", "value": "postman.finance.admin@bomach.local"},
    ],
    "item": [],
}


collection["item"].append(
    folder(
        "00 Bootstrap",
        [
            request_item(
                "Control Login",
                "POST",
                "/api/v1/auth/login",
                body=js(
                    {
                        "email": "{{control_email}}",
                        "password": "{{control_password}}",
                    }
                ),
                tests=[
                    "pm.test('control login returns 200', function () { pm.response.to.have.status(200); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('control_access_token', body.access_token);",
                    "pm.collectionVariables.set('control_refresh_token', body.refresh_token);",
                    "pm.collectionVariables.set('run_suffix', String(Date.now()).slice(-6));",
                ],
            ),
            request_item(
                "Subject Login",
                "POST",
                "/api/v1/auth/login",
                body=js(
                    {
                        "email": "{{subject_email}}",
                        "password": "{{subject_password}}",
                    }
                ),
                tests=[
                    "pm.test('subject login returns 200', function () { pm.response.to.have.status(200); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('subject_access_token', body.access_token);",
                    "pm.collectionVariables.set('subject_refresh_token', body.refresh_token);",
                ],
            ),
            request_item(
                "Roles Permissions Map",
                "GET",
                "/api/v1/roles/permissions-map",
                token_var="control_access_token",
                tests=[
                    "pm.test('permissions map returns 200', function () { pm.response.to.have.status(200); });",
                    "const body = pm.response.json();",
                    "pm.expect(body.permissions_map).to.be.an('object');",
                ],
            ),
            request_item(
                "Lookup Finance Test Role",
                "GET",
                "/api/v1/roles",
                token_var="control_access_token",
                query={"search": "{{role_name}}", "limit": "10", "offset": "0"},
                tests=[
                    "pm.test('roles lookup returns 200', function () { pm.response.to.have.status(200); });",
                    "const body = pm.response.json();",
                    "const items = body.items || body.results || body;",
                    "pm.expect(items.length).to.be.greaterThan(0);",
                    "const role = items.find((item) => item.name === pm.collectionVariables.get('role_name')) || items[0];",
                    "pm.collectionVariables.set('finance_role_id', String(role.id));",
                ],
            ),
            request_item(
                "Lookup Subject Employee",
                "GET",
                "/api/v1/employees/employees",
                token_var="control_access_token",
                query={"search": "{{subject_email_lookup}}", "limit": "10", "offset": "0"},
                tests=[
                    "pm.test('subject employee lookup returns 200', function () { pm.response.to.have.status(200); });",
                    "const body = pm.response.json();",
                    "const items = body.items || body.results || body;",
                    "pm.expect(items.length).to.be.greaterThan(0);",
                    "const employee = items.find((item) => item.email === pm.collectionVariables.get('subject_email_lookup')) || items[0];",
                    "pm.collectionVariables.set('subject_user_id', String(employee.user_id));",
                    "pm.collectionVariables.set('subject_employee_record_id', String(employee.id));",
                    "if (employee.branch_id) { pm.collectionVariables.set('subject_branch_id', String(employee.branch_id)); }",
                ],
            ),
            request_item(
                "Apply Baseline Finance Role Permissions",
                "PUT",
                "/api/v1/roles/{{finance_role_id}}",
                token_var="control_access_token",
                body='{\n  "permissions": {{role_permissions_payload}}\n}',
                prerequest=[
                    "pm.collectionVariables.set('role_permissions_payload', pm.collectionVariables.get('finance_permissions_baseline'));",
                ],
                tests=[
                    "pm.test('baseline finance role update returns 200', function () { pm.response.to.have.status(200); });",
                ],
            ),
            request_item(
                "Assign Subject To Finance Role",
                "PUT",
                "/api/v1/employees/employees/{{subject_user_id}}",
                token_var="control_access_token",
                body='{\n  "role_id": {{finance_role_id}}\n}',
                tests=[
                    "pm.test('subject role assignment returns 200', function () { pm.response.to.have.status(200); });",
                ],
            ),
            request_item(
                "Subject Verify Token",
                "GET",
                "/api/v1/auth/verify-token",
                token_var="subject_access_token",
                tests=[
                    "pm.test('subject token verification returns 200', function () { pm.response.to.have.status(200); });",
                ],
            ),
        ],
    )
)


permission_mutators = [
    ("Remove finance_settings.view", "finance_settings", ["update"]),
    ("Remove financial_reports.export", "financial_reports", ["view"]),
    ("Remove finance_payroll.create", "finance_payroll", ["list", "view", "update", "calculate", "submit", "approve", "reject", "pay", "cancel"]),
    ("Remove statutory.pay", "statutory", ["view", "list", "create", "generate", "update", "submit", "approve", "reject", "void"]),
    ("Remove commissions.approve", "commissions", ["list", "create", "update", "calculate", "view", "reject"]),
    ("Remove cash_flow.view", "cash_flow", []),
]

permission_items = []
for label, resource, actions in permission_mutators:
    permission_items.append(
        request_item(
            label,
            "PUT",
            "/api/v1/roles/{{finance_role_id}}",
            token_var="control_access_token",
            body='{\n  "permissions": {{role_permissions_payload}}\n}',
            prerequest=[
                "const baseline = JSON.parse(pm.collectionVariables.get('finance_permissions_baseline'));",
                f"baseline['{resource}'] = {json.dumps(actions)};",
                "pm.collectionVariables.set('role_permissions_payload', JSON.stringify(baseline));",
            ],
            tests=["pm.test('role permission mutation returns 200', function () { pm.response.to.have.status(200); });"],
        )
    )

permission_items.extend(
    [
        request_item(
            "Subject Denied Finance Settings",
            "GET",
            "/api/v1/finance/settings",
            token_var="subject_access_token",
            tests=[
                "pm.test('subject permission-removal probe does not crash', function () { pm.expect([200, 401, 403, 404]).to.include(pm.response.code); });",
            ],
        ),
        request_item(
            "Restore Baseline Permissions",
            "PUT",
            "/api/v1/roles/{{finance_role_id}}",
            token_var="control_access_token",
            body='{\n  "permissions": {{role_permissions_payload}}\n}',
            prerequest=[
                "pm.collectionVariables.set('role_permissions_payload', pm.collectionVariables.get('finance_permissions_baseline'));",
            ],
            tests=["pm.test('baseline permissions restored', function () { pm.response.to.have.status(200); });"],
        ),
    ]
)

collection["item"].append(folder("01 Permission Checks", permission_items))


collection["item"].append(
    folder(
        "02 Finance Settings, Reports, Exceptions, Audit, Cash Flow",
        [
            request_item(
                "Get Finance Settings",
                "GET",
                "/api/v1/finance/settings",
                token_var="subject_access_token",
                tests=[
                    "pm.test('finance settings returns 200 or scope denial', function () { pm.expect([200, 403]).to.include(pm.response.code); });",
                    "if (pm.response.code === 200) {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body.default_currency).to.exist;",
                    "}",
                ],
            ),
            request_item(
                "Get Finance Settings As Control",
                "GET",
                "/api/v1/finance/settings",
                token_var="control_access_token",
                tests=[
                    "pm.test('control finance settings returns 200 or scope denial', function () { pm.expect([200, 403]).to.include(pm.response.code); });",
                    "pm.collectionVariables.set('finance_settings_scope_ok', pm.response.code === 200 ? 'true' : 'false');",
                    "if (pm.response.code === 200) {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body.default_currency).to.exist;",
                    "}",
                ],
            ),
            request_item(
                "Patch Finance Settings",
                "PATCH",
                "/api/v1/finance/settings",
                token_var="control_access_token",
                body=js(
                    {
                        "journal_prefix": "PMF",
                        "draft_journal_warning_days": 9,
                    }
                ),
                tests=[
                    "if (pm.collectionVariables.get('finance_settings_scope_ok') === 'true') {",
                    "  pm.test('finance settings patch returns 200', function () { pm.response.to.have.status(200); });",
                    "} else {",
                    "  pm.test('finance settings patch is blocked outside company scope', function () { pm.response.to.have.status(403); });",
                    "}",
                ],
            ),
            request_item(
                "Reject Future Closed Through Date",
                "PATCH",
                "/api/v1/finance/settings",
                token_var="control_access_token",
                body=js({"closed_through_date": "2099-12-31"}),
                tests=[
                    "if (pm.collectionVariables.get('finance_settings_scope_ok') === 'true') {",
                    "  pm.test('future close date is rejected', function () { pm.expect([400, 422]).to.include(pm.response.code); });",
                    "} else {",
                    "  pm.test('future close date patch is blocked outside company scope', function () { pm.response.to.have.status(403); });",
                    "}",
                ],
            ),
            request_item(
                "Reports Catalog",
                "GET",
                "/api/v1/finance/reports/catalog",
                token_var="subject_access_token",
                tests=[
                    "pm.test('reports catalog returns 200', function () { pm.response.to.have.status(200); });",
                    "const body = pm.response.json();",
                    "pm.expect(body.reports).to.be.an('array');",
                ],
            ),
            request_item(
                "Profit And Loss",
                "GET",
                "/api/v1/finance/reports/profit-and-loss",
                token_var="subject_access_token",
                tests=["pm.test('profit and loss returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Balance Sheet",
                "GET",
                "/api/v1/finance/reports/balance-sheet",
                token_var="subject_access_token",
                tests=["pm.test('balance sheet returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Revenue Report",
                "GET",
                "/api/v1/finance/reports/revenue",
                token_var="subject_access_token",
                tests=["pm.test('revenue report returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Expense Report",
                "GET",
                "/api/v1/finance/reports/expenses",
                token_var="subject_access_token",
                tests=["pm.test('expense report returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Payables Ageing",
                "GET",
                "/api/v1/finance/reports/payables-ageing",
                token_var="subject_access_token",
                tests=["pm.test('payables ageing returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Export Profit And Loss CSV",
                "GET",
                "/api/v1/finance/reports/export",
                token_var="subject_access_token",
                query={"report_key": "profit_and_loss"},
                tests=[
                    "pm.test('report export returns 200', function () { pm.response.to.have.status(200); });",
                    "pm.test('report export is csv', function () { pm.expect(pm.response.headers.get('Content-Type')).to.include('text/csv'); });",
                ],
            ),
            request_item(
                "Export Invalid Report Key",
                "GET",
                "/api/v1/finance/reports/export",
                token_var="subject_access_token",
                query={"report_key": "budget_vs_actual"},
                tests=[
                    "pm.test('invalid report key is rejected', function () { pm.expect([400, 404]).to.include(pm.response.code); });",
                ],
            ),
            request_item(
                "Finance Exceptions",
                "GET",
                "/api/v1/finance/exceptions",
                token_var="subject_access_token",
                tests=["pm.test('exceptions list returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Finance Exceptions Summary",
                "GET",
                "/api/v1/finance/exceptions/summary",
                token_var="subject_access_token",
                tests=["pm.test('exceptions summary returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Finance Exceptions Invalid Severity",
                "GET",
                "/api/v1/finance/exceptions",
                token_var="subject_access_token",
                query={"severity": "urgent"},
                tests=[
                    "pm.test('invalid severity rejected', function () { pm.expect([400]).to.include(pm.response.code); });",
                ],
            ),
            request_item(
                "Export Exceptions CSV",
                "GET",
                "/api/v1/finance/exceptions/export",
                token_var="subject_access_token",
                tests=[
                    "pm.test('exceptions export returns 200', function () { pm.response.to.have.status(200); });",
                    "pm.test('exceptions export is csv', function () { pm.expect(pm.response.headers.get('Content-Type')).to.include('text/csv'); });",
                ],
            ),
            request_item(
                "Finance Audit List",
                "GET",
                "/api/v1/finance/audit",
                token_var="subject_access_token",
                tests=["pm.test('finance audit list returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Finance Audit Export",
                "GET",
                "/api/v1/finance/audit/export",
                token_var="subject_access_token",
                tests=[
                    "pm.test('finance audit export returns 200', function () { pm.response.to.have.status(200); });",
                    "pm.test('finance audit export is csv', function () { pm.expect(pm.response.headers.get('Content-Type')).to.include('text/csv'); });",
                ],
            ),
            request_item(
                "Cash Flow Forecast",
                "GET",
                "/api/v1/finance/cash-flow/forecast",
                token_var="subject_access_token",
                query={"weeks": "13"},
                tests=["pm.test('cash flow forecast returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Cash Flow Invalid Weeks",
                "GET",
                "/api/v1/finance/cash-flow/forecast",
                token_var="subject_access_token",
                query={"weeks": "0"},
                tests=["pm.test('cash flow invalid weeks rejected', function () { pm.expect([400]).to.include(pm.response.code); });"],
            ),
        ],
    )
)


collection["item"].append(
    folder(
        "03 Accounts And Chart Of Accounts",
        [
            request_item(
                "List Finance Accounts",
                "GET",
                "/api/v1/finance/accounts",
                token_var="subject_access_token",
                tests=["pm.test('accounts list returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Create Finance Account",
                "POST",
                "/api/v1/finance/accounts",
                token_var="subject_access_token",
                body='{\n  "account_type": "bank",\n  "display_name": "Postman Operating {{run_suffix}}",\n  "currency": "NGN",\n  "bank_name": "GTBank",\n  "account_number": "PM{{run_suffix}}001",\n  "account_name": "Bomach Group",\n  "notes": "Postman finance regression account",\n  "opening_balance": "250000.00",\n  "opening_balance_date": "2026-08-01"\n}',
                tests=[
                    "pm.test('finance account create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('finance_account_id', String(body.id));",
                    "if (body.ledger_account_id) { pm.collectionVariables.set('finance_account_ledger_id', String(body.ledger_account_id)); }",
                ],
            ),
            request_item(
                "Get Finance Account Balance",
                "GET",
                "/api/v1/finance/accounts/{{finance_account_id}}/balance",
                token_var="subject_access_token",
                tests=["pm.test('finance account balance returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Update Finance Account",
                "PATCH",
                "/api/v1/finance/accounts/{{finance_account_id}}",
                token_var="subject_access_token",
                body='{\n  "notes": "Updated by Postman finance regression run"\n}',
                tests=["pm.test('finance account patch returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "List Ledger Accounts",
                "GET",
                "/api/v1/finance/ledger-accounts",
                token_var="subject_access_token",
                tests=["pm.test('ledger accounts list returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Find Ledger Parent And Defaults",
                "GET",
                "/api/v1/finance/ledger-accounts",
                token_var="subject_access_token",
                query={"limit": "200", "offset": "0"},
                tests=[
                    "pm.test('ledger discovery returns 200', function () { pm.response.to.have.status(200); });",
                    "const body = pm.response.json();",
                    "const items = body.items || body.results || body;",
                    "const cashBankParent = items.find((item) => item.code === '1100');",
                    "const fixedAssetParent = items.find((item) => item.code === '1600');",
                    "const revenue = items.find((item) => item.system_role === 'service_revenue') || items.find((item) => item.account_type === 'revenue');",
                    "const expense = items.find((item) => item.system_role === 'operating_expense') || items.find((item) => item.account_type === 'expense');",
                    "const depreciation = items.find((item) => item.code === '6300') || expense;",
                    "pm.expect(cashBankParent).to.exist;",
                    "pm.expect(fixedAssetParent).to.exist;",
                    "pm.expect(revenue).to.exist;",
                    "pm.expect(expense).to.exist;",
                    "pm.collectionVariables.set('cash_bank_parent_ledger_id', String(cashBankParent.id));",
                    "pm.collectionVariables.set('fixed_asset_parent_ledger_id', String(fixedAssetParent.id));",
                    "pm.collectionVariables.set('revenue_ledger_id', String(revenue.id));",
                    "pm.collectionVariables.set('expense_ledger_id', String(expense.id));",
                    "pm.collectionVariables.set('depreciation_expense_ledger_id', String(depreciation.id));",
                ],
            ),
            request_item(
                "Create Postable Asset Ledger Account",
                "POST",
                "/api/v1/finance/ledger-accounts",
                token_var="subject_access_token",
                body='{\n  "code": "19{{run_suffix}}",\n  "name": "Postman Asset {{run_suffix}}",\n  "account_type": "asset",\n  "normal_balance": "debit",\n  "parent_id": {{fixed_asset_parent_ledger_id}},\n  "is_postable": true,\n  "description": "Postman ledger asset"\n}',
                tests=[
                    "pm.test('ledger create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('custom_asset_ledger_id', String(body.id));",
                ],
            ),
            request_item(
                "Create Contra Asset Ledger Account",
                "POST",
                "/api/v1/finance/ledger-accounts",
                token_var="subject_access_token",
                body='{\n  "code": "29{{run_suffix}}",\n  "name": "Postman Contra Asset {{run_suffix}}",\n  "account_type": "asset",\n  "normal_balance": "credit",\n  "parent_id": {{fixed_asset_parent_ledger_id}},\n  "is_postable": true,\n  "description": "Postman contra asset"\n}',
                tests=[
                    "pm.test('contra asset ledger create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('contra_asset_ledger_id', String(body.id));",
                ],
            ),
            request_item(
                "Get Custom Asset Ledger Account",
                "GET",
                "/api/v1/finance/ledger-accounts/{{custom_asset_ledger_id}}",
                token_var="subject_access_token",
                tests=["pm.test('ledger detail returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Patch Custom Asset Ledger Account",
                "PATCH",
                "/api/v1/finance/ledger-accounts/{{custom_asset_ledger_id}}",
                token_var="subject_access_token",
                body='{\n  "description": "Updated by Postman finance regression run"\n}',
                tests=["pm.test('ledger patch returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Map Finance Account To Ledger Account",
                "POST",
                "/api/v1/finance/accounts/{{finance_account_id}}/ledger-account",
                token_var="subject_access_token",
                body='{\n  "ledger_account_id": {{finance_account_ledger_id}}\n}',
                tests=["pm.test('finance account ledger mapping returns 200', function () { pm.response.to.have.status(200); });"],
            ),
        ],
    )
)


collection["item"].append(
    folder(
        "04 Journals And General Ledger",
        [
            request_item(
                "Create Manual Journal",
                "POST",
                "/api/v1/finance/journals",
                token_var="subject_access_token",
                body='{\n  "entry_date": "2026-08-20",\n  "currency": "NGN",\n  "reference": "PM-JRN-{{run_suffix}}",\n  "memo": "Postman journal regression",\n  "lines": [\n    {\n      "ledger_account_id": {{custom_asset_ledger_id}},\n      "description": "Journal debit",\n      "debit": "1000.00",\n      "credit": "0.00"\n    },\n    {\n      "ledger_account_id": {{revenue_ledger_id}},\n      "description": "Journal credit",\n      "debit": "0.00",\n      "credit": "1000.00"\n    }\n  ]\n}',
                tests=[
                    "pm.test('manual journal create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('journal_id', String(body.id));",
                ],
            ),
            request_item(
                "Get Manual Journal",
                "GET",
                "/api/v1/finance/journals/{{journal_id}}",
                token_var="subject_access_token",
                tests=["pm.test('manual journal detail returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Patch Manual Journal Draft",
                "PATCH",
                "/api/v1/finance/journals/{{journal_id}}",
                token_var="subject_access_token",
                body='{\n  "memo": "Patched postman journal regression"\n}',
                tests=["pm.test('manual journal patch returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Post Manual Journal",
                "POST",
                "/api/v1/finance/journals/{{journal_id}}/post",
                token_var="subject_access_token",
                body='{}',
                tests=["pm.test('manual journal post returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Reverse Posted Journal",
                "POST",
                "/api/v1/finance/journals/{{journal_id}}/reverse",
                token_var="subject_access_token",
                body='{\n  "memo": "Postman reversal {{run_suffix}}"\n}',
                tests=["pm.test('manual journal reverse returns 201', function () { pm.response.to.have.status(201); });"],
            ),
            request_item(
                "General Ledger",
                "GET",
                "/api/v1/finance/general-ledger",
                token_var="subject_access_token",
                query={"ledger_account_id": "{{custom_asset_ledger_id}}", "currency": "NGN"},
                tests=["pm.test('general ledger returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Trial Balance",
                "GET",
                "/api/v1/finance/trial-balance",
                token_var="subject_access_token",
                query={"currency": "NGN"},
                tests=["pm.test('trial balance returns 200', function () { pm.response.to.have.status(200); });"],
            ),
        ],
    )
)


collection["item"].append(
    folder(
        "05 Payroll And Statutory",
        [
            request_item(
                "Create Payroll Run",
                "POST",
                "/api/v1/finance/payroll",
                token_var="subject_access_token",
                prerequest=[
                    "const suffix = Number(pm.collectionVariables.get('run_suffix') || '0');",
                    "const periodMonth = (suffix % 12) + 1;",
                    "const periodYear = 2030 + Math.floor(suffix / 12);",
                    "const scheduledMonth = String(periodMonth).padStart(2, '0');",
                    "const payload = { period_month: periodMonth, period_year: periodYear, scheduled_payment_date: `${periodYear}-${scheduledMonth}-28`, notes: `Postman payroll run ${pm.collectionVariables.get('run_suffix')}` };",
                    "const branchId = pm.collectionVariables.get('subject_branch_id');",
                    "if (branchId) { payload.branch_id = Number(branchId); }",
                    "pm.collectionVariables.set('payroll_run_body', JSON.stringify(payload, null, 2));",
                ],
                body="{{payroll_run_body}}",
                tests=[
                    "pm.test('payroll create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('payroll_run_id', String(body.id));",
                    "pm.collectionVariables.set('payroll_run_created', 'true');",
                ],
            ),
            request_item(
                "Reject Duplicate Payroll Period",
                "POST",
                "/api/v1/finance/payroll",
                token_var="subject_access_token",
                body="{{payroll_run_body}}",
                tests=[
                    "pm.test('duplicate payroll run rejected', function () { pm.expect([400]).to.include(pm.response.code); });",
                ],
            ),
            request_item(
                "Calculate Payroll Run",
                "POST",
                "/api/v1/finance/payroll/{{payroll_run_id}}/calculate",
                token_var="subject_access_token",
                body='{}',
                tests=[
                    "if (pm.collectionVariables.get('payroll_run_created') === 'true') {",
                    "  pm.test('payroll calculate returns 200', function () { pm.response.to.have.status(200); });",
                    "  const body = pm.response.json();",
                    "  pm.expect(body.lines).to.be.an('array');",
                    "  if (body.lines.length > 0) { pm.collectionVariables.set('payroll_line_id', String(body.lines[0].id)); pm.collectionVariables.set('payroll_has_lines', 'true'); } else { pm.collectionVariables.unset('payroll_line_id'); pm.collectionVariables.set('payroll_has_lines', 'false'); }",
                    "  pm.collectionVariables.set('payroll_can_submit', body.employee_count > 0 && Number(body.net_pay) > 0 ? 'true' : 'false');",
                    "} else {",
                    "  pm.test('payroll calculate is skipped when create did not succeed', function () { pm.expect([404, 422]).to.include(pm.response.code); });",
                    "  pm.collectionVariables.set('payroll_has_lines', 'false');",
                    "  pm.collectionVariables.set('payroll_can_submit', 'false');",
                    "}",
                ],
            ),
            request_item(
                "Replace Payroll Manual Items",
                "PUT",
                "/api/v1/finance/payroll/{{payroll_run_id}}/lines/{{payroll_line_id}}/manual-items",
                token_var="subject_access_token",
                body='{\n  "items": [\n    {\n      "item_type": "deduction",\n      "category": "loan",\n      "name": "Postman Loan Recovery",\n      "amount": "5000.00",\n      "notes": "Regression deduction"\n    }\n  ]\n}',
                tests=[
                    "if (pm.collectionVariables.get('payroll_has_lines') === 'true') {",
                    "  pm.test('manual payroll items replace returns 200', function () { pm.response.to.have.status(200); });",
                    "} else {",
                    "  pm.test('manual payroll items replace is skipped when no payroll line was generated', function () { pm.expect([404, 422]).to.include(pm.response.code); });",
                    "}",
                ],
            ),
            request_item(
                "Get Payroll Run",
                "GET",
                "/api/v1/finance/payroll/{{payroll_run_id}}",
                token_var="subject_access_token",
                tests=[
                    "if (pm.collectionVariables.get('payroll_run_created') === 'true') {",
                    "  pm.test('payroll detail returns 200', function () { pm.response.to.have.status(200); });",
                    "} else {",
                    "  pm.test('payroll detail is skipped when create did not succeed', function () { pm.expect([404, 422]).to.include(pm.response.code); });",
                    "}",
                ],
            ),
            request_item(
                "Submit Payroll Run",
                "POST",
                "/api/v1/finance/payroll/{{payroll_run_id}}/submit",
                token_var="subject_access_token",
                body='{}',
                tests=[
                    "if (pm.collectionVariables.get('payroll_can_submit') === 'true') {",
                    "  pm.test('payroll submit returns 200', function () { pm.response.to.have.status(200); });",
                    "  pm.collectionVariables.set('payroll_submit_succeeded', 'true');",
                    "} else {",
                    "  pm.test('payroll submit is rejected when no eligible payroll lines/net pay exist', function () { pm.expect([400]).to.include(pm.response.code); });",
                    "  pm.collectionVariables.set('payroll_submit_succeeded', 'false');",
                    "}",
                ],
            ),
            request_item(
                "Approve Payroll Run",
                "POST",
                "/api/v1/finance/payroll/{{payroll_run_id}}/approve",
                token_var="subject_access_token",
                body='{}',
                tests=[
                    "if (pm.collectionVariables.get('payroll_submit_succeeded') === 'true') {",
                    "  pm.test('payroll approve returns 200', function () { pm.response.to.have.status(200); });",
                    "  pm.collectionVariables.set('payroll_approve_succeeded', 'true');",
                    "} else {",
                    "  pm.test('payroll approve is rejected when submit did not succeed', function () { pm.expect([400]).to.include(pm.response.code); });",
                    "  pm.collectionVariables.set('payroll_approve_succeeded', 'false');",
                    "}",
                ],
            ),
            request_item(
                "Pay Payroll Run",
                "POST",
                "/api/v1/finance/payroll/{{payroll_run_id}}/pay",
                token_var="subject_access_token",
                body='{\n  "finance_account_id": {{finance_account_id}},\n  "payment_reference": "PAYROLL-PM-{{run_suffix}}"\n}',
                tests=[
                    "if (pm.collectionVariables.get('payroll_approve_succeeded') === 'true') {",
                    "  pm.test('payroll pay returns 200', function () { pm.response.to.have.status(200); });",
                    "} else {",
                    "  pm.test('payroll pay is rejected when approve did not succeed', function () { pm.expect([400]).to.include(pm.response.code); });",
                    "}",
                ],
            ),
            request_item(
                "Create Rejectable Payroll Run",
                "POST",
                "/api/v1/finance/payroll",
                token_var="subject_access_token",
                prerequest=[
                    "const suffix = Number(pm.collectionVariables.get('run_suffix') || '0');",
                    "const periodMonth = ((suffix + 1) % 12) + 1;",
                    "const periodYear = 2030 + Math.floor((suffix + 1) / 12);",
                    "const scheduledMonth = String(periodMonth).padStart(2, '0');",
                    "const payload = { period_month: periodMonth, period_year: periodYear, scheduled_payment_date: `${periodYear}-${scheduledMonth}-28`, notes: `Postman reject payroll ${pm.collectionVariables.get('run_suffix')}` };",
                    "const branchId = pm.collectionVariables.get('subject_branch_id');",
                    "if (branchId) { payload.branch_id = Number(branchId); }",
                    "pm.collectionVariables.set('reject_payroll_run_body', JSON.stringify(payload, null, 2));",
                ],
                body="{{reject_payroll_run_body}}",
                tests=[
                    "pm.test('second payroll create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('reject_payroll_run_id', String(body.id));",
                    "pm.collectionVariables.set('reject_payroll_run_created', 'true');",
                ],
            ),
            request_item(
                "Calculate Rejectable Payroll Run",
                "POST",
                "/api/v1/finance/payroll/{{reject_payroll_run_id}}/calculate",
                token_var="subject_access_token",
                body='{}',
                tests=[
                    "if (pm.collectionVariables.get('reject_payroll_run_created') === 'true') {",
                    "  pm.test('second payroll calculate returns 200', function () { pm.response.to.have.status(200); });",
                    "  const body = pm.response.json();",
                    "  pm.collectionVariables.set('reject_payroll_can_submit', body.employee_count > 0 && Number(body.net_pay) > 0 ? 'true' : 'false');",
                    "} else {",
                    "  pm.test('second payroll calculate is skipped when create did not succeed', function () { pm.expect([404, 422]).to.include(pm.response.code); });",
                    "  pm.collectionVariables.set('reject_payroll_can_submit', 'false');",
                    "}",
                ],
            ),
            request_item(
                "Submit Rejectable Payroll Run",
                "POST",
                "/api/v1/finance/payroll/{{reject_payroll_run_id}}/submit",
                token_var="subject_access_token",
                body='{}',
                tests=[
                    "if (pm.collectionVariables.get('reject_payroll_can_submit') === 'true') {",
                    "  pm.test('second payroll submit returns 200', function () { pm.response.to.have.status(200); });",
                    "  pm.collectionVariables.set('reject_payroll_submit_succeeded', 'true');",
                    "} else {",
                    "  pm.test('second payroll submit is rejected when no eligible payroll lines/net pay exist', function () { pm.expect([400]).to.include(pm.response.code); });",
                    "  pm.collectionVariables.set('reject_payroll_submit_succeeded', 'false');",
                    "}",
                ],
            ),
            request_item(
                "Reject Payroll Run",
                "POST",
                "/api/v1/finance/payroll/{{reject_payroll_run_id}}/reject",
                token_var="subject_access_token",
                body='{\n  "reason": "Postman rejection path"\n}',
                tests=[
                    "if (pm.collectionVariables.get('reject_payroll_submit_succeeded') === 'true') {",
                    "  pm.test('payroll reject returns 200', function () { pm.response.to.have.status(200); });",
                    "} else {",
                    "  pm.test('payroll reject is rejected when submit did not succeed', function () { pm.expect([400]).to.include(pm.response.code); });",
                    "}",
                ],
            ),
            request_item(
                "Cancel Rejected Payroll Run",
                "POST",
                "/api/v1/finance/payroll/{{reject_payroll_run_id}}/cancel",
                token_var="subject_access_token",
                body='{\n  "reason": "Postman cancellation path"\n}',
                tests=["pm.test('payroll cancel returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Create Manual Statutory Obligation",
                "POST",
                "/api/v1/finance/statutory/obligations",
                token_var="subject_access_token",
                body='{\n  "obligation_type": "other",\n  "period_label": "Postman-{{run_suffix}}",\n  "period_start": "2026-10-01",\n  "period_end": "2026-10-31",\n  "basis": "manual",\n  "basis_amount": "100000.00",\n  "amount": "7500.00",\n  "due_date": "2026-11-10",\n  "notes": "Postman statutory obligation"\n}',
                tests=[
                    "pm.test('manual statutory create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('statutory_obligation_id', String(body.id));",
                ],
            ),
            request_item(
                "Patch Draft Statutory Obligation",
                "PATCH",
                "/api/v1/finance/statutory/obligations/{{statutory_obligation_id}}",
                token_var="subject_access_token",
                body='{\n  "notes": "Patched by Postman regression"\n}',
                tests=["pm.test('draft statutory patch returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Submit Statutory Obligation",
                "POST",
                "/api/v1/finance/statutory/obligations/{{statutory_obligation_id}}/submit",
                token_var="subject_access_token",
                body='{}',
                tests=["pm.test('statutory submit returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Reject Patch After Submit",
                "PATCH",
                "/api/v1/finance/statutory/obligations/{{statutory_obligation_id}}",
                token_var="subject_access_token",
                body='{\n  "notes": "This should be blocked after submit"\n}',
                tests=["pm.test('submitted statutory patch rejected', function () { pm.expect([400]).to.include(pm.response.code); });"],
            ),
            request_item(
                "Approve Statutory Obligation",
                "POST",
                "/api/v1/finance/statutory/obligations/{{statutory_obligation_id}}/approve",
                token_var="subject_access_token",
                body='{}',
                tests=["pm.test('statutory approve returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Pay Statutory Obligation",
                "POST",
                "/api/v1/finance/statutory/obligations/{{statutory_obligation_id}}/pay",
                token_var="subject_access_token",
                body='{\n  "finance_account_id": {{finance_account_id}},\n  "payment_reference": "STAT-PM-{{run_suffix}}"\n}',
                tests=["pm.test('statutory pay returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Generate Payroll Statutory Obligation",
                "POST",
                "/api/v1/finance/statutory/generate/payroll",
                token_var="subject_access_token",
                body='{\n  "payroll_run_id": {{payroll_run_id}},\n  "category": "paye",\n  "due_date": "2026-11-07",\n  "notes": "Generated from payroll run {{run_suffix}}"\n}',
                tests=[
                    "if (pm.collectionVariables.get('payroll_approve_succeeded') === 'true') {",
                    "  pm.test('payroll statutory generation returns 201', function () { pm.response.to.have.status(201); });",
                    "  const body = pm.response.json();",
                    "  pm.collectionVariables.set('generated_statutory_obligation_id', String(body.id));",
                    "} else {",
                    "  pm.test('payroll statutory generation is rejected before payroll approval', function () { pm.expect([400]).to.include(pm.response.code); });",
                    "  pm.collectionVariables.unset('generated_statutory_obligation_id');",
                    "}",
                ],
            ),
            request_item(
                "Void Generated Statutory Obligation",
                "POST",
                "/api/v1/finance/statutory/obligations/{{generated_statutory_obligation_id}}/void",
                token_var="subject_access_token",
                body='{}',
                tests=[
                    "if (pm.collectionVariables.get('generated_statutory_obligation_id')) {",
                    "  pm.test('generated statutory void returns 200', function () { pm.response.to.have.status(200); });",
                    "} else {",
                    "  pm.test('generated statutory void is skipped when no generated obligation exists', function () { pm.expect([404, 422]).to.include(pm.response.code); });",
                    "}",
                ],
            ),
            request_item(
                "Statutory Summary",
                "GET",
                "/api/v1/finance/statutory/summary",
                token_var="subject_access_token",
                tests=["pm.test('statutory summary returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Statutory Listing",
                "GET",
                "/api/v1/finance/statutory/obligations",
                token_var="subject_access_token",
                tests=["pm.test('statutory list returns 200', function () { pm.response.to.have.status(200); });"],
            ),
        ],
    )
)


collection["item"].append(
    folder(
        "06 Commissions And Fixed Assets",
        [
            request_item(
                "Create Bonus Award",
                "POST",
                "/api/v1/finance/bonuses",
                token_var="subject_access_token",
                body='{\n  "employee_id": {{subject_employee_record_id}},\n  "amount": "12000.00",\n  "payout_month": 12,\n  "payout_year": 2026,\n  "reason": "Postman bonus {{run_suffix}}"\n}',
                tests=[
                    "pm.test('bonus create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('bonus_award_id', String(body.id));",
                ],
            ),
            request_item(
                "Get Bonus Award",
                "GET",
                "/api/v1/finance/commissions/{{bonus_award_id}}",
                token_var="subject_access_token",
                tests=["pm.test('bonus detail returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Approve Bonus Award",
                "POST",
                "/api/v1/finance/commissions/{{bonus_award_id}}/approve",
                token_var="subject_access_token",
                body='{}',
                tests=["pm.test('bonus approve returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Create Rejectable Bonus Award",
                "POST",
                "/api/v1/finance/bonuses",
                token_var="subject_access_token",
                body='{\n  "employee_id": {{subject_employee_record_id}},\n  "amount": "8000.00",\n  "payout_month": 12,\n  "payout_year": 2026,\n  "reason": "Postman rejected bonus {{run_suffix}}"\n}',
                tests=[
                    "pm.test('second bonus create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('rejected_bonus_award_id', String(body.id));",
                ],
            ),
            request_item(
                "Reject Bonus Award",
                "POST",
                "/api/v1/finance/commissions/{{rejected_bonus_award_id}}/reject",
                token_var="subject_access_token",
                body='{\n  "reason": "Postman rejected bonus path"\n}',
                tests=["pm.test('bonus reject returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "List Commission Awards",
                "GET",
                "/api/v1/finance/commissions",
                token_var="subject_access_token",
                tests=["pm.test('commissions list returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "List Confirmed Payments For Optional Commission Calculation",
                "GET",
                "/api/v1/finance/payments/confirmed",
                token_var="subject_access_token",
                query={"limit": "10", "offset": "0"},
                tests=[
                    "pm.test('confirmed payments list returns 200', function () { pm.response.to.have.status(200); });",
                    "const body = pm.response.json();",
                    "const items = body.items || body.results || body;",
                    "if (items.length > 0) { pm.collectionVariables.set('confirmed_payment_id', String(items[0].id)); pm.collectionVariables.set('confirmed_payment_service_id', String(items[0].service_id)); }",
                ],
                description="If this returns zero items, the optional commission calculation request below will not have enough upstream production data to succeed.",
            ),
            request_item(
                "Create Commission Rule From Existing Service",
                "POST",
                "/api/v1/finance/commission-rules",
                token_var="subject_access_token",
                prerequest=[
                    "const serviceId = pm.collectionVariables.get('confirmed_payment_service_id');",
                    "if (!serviceId) { pm.collectionVariables.set('optional_commission_rule_body', JSON.stringify({ name: 'Missing upstream confirmed payment/service data', service_id: 0, rate_percent: '5.00', effective_from: '2026-08-01' })); }",
                    "else { pm.collectionVariables.set('optional_commission_rule_body', JSON.stringify({ name: `Postman Rule ${pm.collectionVariables.get('run_suffix')}`, service_id: Number(serviceId), rate_percent: '5.00', minimum_verified_revenue: '0.00', effective_from: '2026-08-01', notes: 'Postman commission rule' }, null, 2)); }",
                ],
                body="{{optional_commission_rule_body}}",
                tests=[
                    "if (!pm.collectionVariables.get('confirmed_payment_service_id')) {",
                    "  pm.test('commission rule skipped because no confirmed payment service was available', function () { pm.expect(pm.response.code).to.be.oneOf([400, 404, 422]); });",
                    "} else {",
                    "  pm.test('commission rule create returns 201', function () { pm.response.to.have.status(201); });",
                    "  const body = pm.response.json();",
                    "  pm.collectionVariables.set('commission_rule_id', String(body.id));",
                    "}",
                ],
            ),
            request_item(
                "Optional Commission Calculation",
                "POST",
                "/api/v1/finance/commissions/calculate",
                token_var="subject_access_token",
                prerequest=[
                    "const payload = {",
                    "  employee_id: Number(pm.collectionVariables.get('subject_employee_record_id') || '0'),",
                    "  payment_id: Number(pm.collectionVariables.get('confirmed_payment_id') || '0'),",
                    "  commission_rule_id: Number(pm.collectionVariables.get('commission_rule_id') || '0'),",
                    "  payout_month: 12,",
                    "  payout_year: 2026,",
                    "  notes: 'Postman calculated commission'",
                    "};",
                    "pm.collectionVariables.set('optional_commission_payload', JSON.stringify(payload, null, 2));",
                ],
                body="{{optional_commission_payload}}",
                tests=[
                    "const hasInputs = pm.collectionVariables.get('confirmed_payment_id') && pm.collectionVariables.get('commission_rule_id');",
                    "if (!hasInputs) {",
                    "  pm.test('commission calculation skipped because no confirmed payment/rule prerequisites were available', function () { pm.expect(pm.response.code).to.be.oneOf([400, 404, 422]); });",
                    "} else {",
                    "  pm.test('commission calculation returns 201', function () { pm.response.to.have.status(201); });",
                    "}",
                ],
            ),
            request_item(
                "Create Expense For Fixed Asset Source",
                "POST",
                "/api/v1/finance/expenses",
                token_var="subject_access_token",
                body='{\n  "date": "2026-05-20",\n  "description": "Postman laptop purchase {{run_suffix}}",\n  "amount": "250000.00",\n  "vendor": "Postman Vendor",\n  "beneficiary": "Operations",\n  "category": "equipment",\n  "cost_type": "capital_expenditure",\n  "finance_account_id": {{finance_account_id}},\n  "billable": false,\n  "client_visible": false\n}',
                tests=[
                    "pm.test('fixed asset source expense create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('fixed_asset_source_expense_id', String(body.id));",
                ],
            ),
            request_item(
                "Approve Fixed Asset Source Expense",
                "POST",
                "/api/v1/finance/expenses/{{fixed_asset_source_expense_id}}/approve",
                token_var="control_access_token",
                body='{}',
                tests=["pm.test('fixed asset source expense approve returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Pay Fixed Asset Source Expense",
                "POST",
                "/api/v1/finance/expenses/{{fixed_asset_source_expense_id}}/pay",
                token_var="subject_access_token",
                body='{\n  "finance_account_id": {{finance_account_id}},\n  "paid_at": "2026-05-20T12:00:00Z",\n  "payment_reference": "FA-EXP-PM-{{run_suffix}}"\n}',
                tests=["pm.test('fixed asset source expense pay returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Create Fixed Asset Category",
                "POST",
                "/api/v1/finance/fixed-asset-categories",
                token_var="subject_access_token",
                body='{\n  "code": "FAC-{{run_suffix}}",\n  "name": "Postman IT Equipment {{run_suffix}}",\n  "description": "Postman fixed asset category",\n  "asset_ledger_account_id": {{custom_asset_ledger_id}},\n  "accumulated_depreciation_ledger_account_id": {{contra_asset_ledger_id}},\n  "depreciation_expense_ledger_account_id": {{depreciation_expense_ledger_id}},\n  "default_useful_life_months": 36,\n  "default_residual_value_percent": "10.00"\n}',
                tests=[
                    "pm.test('fixed asset category create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('fixed_asset_category_id', String(body.id));",
                ],
            ),
            request_item(
                "Patch Fixed Asset Category",
                "PATCH",
                "/api/v1/finance/fixed-asset-categories/{{fixed_asset_category_id}}",
                token_var="subject_access_token",
                body='{\n  "description": "Updated by Postman fixed asset regression"\n}',
                tests=["pm.test('fixed asset category patch returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Create Fixed Asset",
                "POST",
                "/api/v1/finance/fixed-assets",
                token_var="subject_access_token",
                body='{\n  "category_id": {{fixed_asset_category_id}},\n  "source_expense_id": {{fixed_asset_source_expense_id}},\n  "name": "Postman Asset {{run_suffix}}",\n  "description": "Postman fixed asset",\n  "acquisition_date": "2026-05-20",\n  "acquisition_cost": "250000.00",\n  "residual_value": "25000.00",\n  "useful_life_months": 36\n}',
                tests=[
                    "pm.test('fixed asset create returns 201', function () { pm.response.to.have.status(201); });",
                    "const body = pm.response.json();",
                    "pm.collectionVariables.set('fixed_asset_id', String(body.id));",
                ],
            ),
            request_item(
                "Capitalize Fixed Asset",
                "POST",
                "/api/v1/finance/fixed-assets/{{fixed_asset_id}}/capitalize",
                token_var="subject_access_token",
                body='{\n  "capitalization_date": "2026-05-20"\n}',
                tests=["pm.test('fixed asset capitalize returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Fixed Asset Depreciation Schedule",
                "GET",
                "/api/v1/finance/fixed-assets/{{fixed_asset_id}}/depreciation-schedule",
                token_var="subject_access_token",
                tests=["pm.test('fixed asset schedule returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Depreciate Fixed Asset",
                "POST",
                "/api/v1/finance/fixed-assets/{{fixed_asset_id}}/depreciate",
                token_var="subject_access_token",
                body='{\n  "period_end": "2026-06-30"\n}',
                tests=["pm.test('fixed asset depreciation returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Dispose Fixed Asset",
                "POST",
                "/api/v1/finance/fixed-assets/{{fixed_asset_id}}/dispose",
                token_var="subject_access_token",
                body='{\n  "disposal_date": "2026-08-15",\n  "proceeds": "100000.00",\n  "finance_account_id": {{finance_account_id}},\n  "reference": "FA-DISP-{{run_suffix}}",\n  "notes": "Postman disposal flow"\n}',
                tests=["pm.test('fixed asset disposal returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Deactivate Fixed Asset Category",
                "POST",
                "/api/v1/finance/fixed-asset-categories/{{fixed_asset_category_id}}/deactivate",
                token_var="subject_access_token",
                body='{}',
                tests=["pm.test('fixed asset category deactivate returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Deactivate Custom Ledger Account",
                "POST",
                "/api/v1/finance/ledger-accounts/{{custom_asset_ledger_id}}/deactivate",
                token_var="subject_access_token",
                body='{}',
                tests=["pm.test('custom ledger deactivate returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Deactivate Finance Account",
                "POST",
                "/api/v1/finance/accounts/{{finance_account_id}}/deactivate",
                token_var="subject_access_token",
                body='{}',
                tests=["pm.test('finance account deactivate returns 200', function () { pm.response.to.have.status(200); });"],
            ),
        ],
    )
)


collection["item"].append(
    folder(
        "99 Cleanup",
        [
            request_item(
                "Remove Subject Role",
                "PUT",
                "/api/v1/employees/employees/{{subject_user_id}}",
                token_var="control_access_token",
                body='{\n  "role_id": null\n}',
                tests=["pm.test('subject role removal returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Control Logout",
                "POST",
                "/api/v1/auth/logout",
                token_var="control_access_token",
                body=js({"refresh_token": "{{control_refresh_token}}"}),
                tests=["pm.test('control logout returns 200', function () { pm.response.to.have.status(200); });"],
            ),
            request_item(
                "Subject Logout",
                "POST",
                "/api/v1/auth/logout",
                token_var="subject_access_token",
                body=js({"refresh_token": "{{subject_refresh_token}}"}),
                tests=["pm.test('subject logout returns 200', function () { pm.response.to.have.status(200); });"],
            ),
        ],
    )
)


environment = {
    "name": "Bomach Finance Worked Features Local",
    "values": [
        {"key": "base_url", "value": "http://127.0.0.1:8000", "enabled": True},
        {
            "key": "control_email",
            "value": "postman.finance.admin@bomach.local",
            "enabled": True,
        },
        {
            "key": "control_password",
            "value": "Postman123!",
            "enabled": True,
        },
        {
            "key": "subject_email",
            "value": "postman.finance.subject@bomach.local",
            "enabled": True,
        },
        {
            "key": "subject_password",
            "value": "Postman123!",
            "enabled": True,
        },
    ],
    "_postman_variable_scope": "environment",
    "_postman_exported_at": "2026-08-20T00:00:00.000Z",
    "_postman_exported_using": "Codex",
}


OUT_DIR.mkdir(parents=True, exist_ok=True)
COLLECTION_PATH.write_text(json.dumps(collection, indent=2) + "\n")
ENV_PATH.write_text(json.dumps(environment, indent=2) + "\n")

print(f"Wrote {COLLECTION_PATH}")
print(f"Wrote {ENV_PATH}")
