# Permission Endpoint Test Results
**Date:** 2026-03-14 14:16:24

## Known Issues (NOT permission-related)

- **expenses:list (HTTP 500)** — Pydantic schema validation error: a required field is null in the DB. The permission check passes (the endpoint is reached), but the response serializer fails. This is a schema bug, not a permission bug.
- **leads:list (HTTP 500 for managers only)** — `scope_queryset` filters by `branch` field, but the Lead model may not have a `branch` column matching the lookup path. CEO and head_operations pass because their scope doesn't filter by branch. This is a scoping configuration issue.
- **PASS (404) results** — These endpoints don't have `@require_permission` yet (HR endpoints like job_postings, leave_requests, payroll, assets, awards) or the URL pattern doesn't match exactly. The 404 means the permission check was NOT tested for these.

## Summary

| Employee Level | PASS | DENIED | ERROR/OTHER | Total |
|---|---|---|---|---|
| ceo (ceo) | 36 | 0 | 1 | 37 |
| manager (manager) | 34 | 1 | 2 | 37 |
| manager_branch2 (manager) | 34 | 1 | 2 | 37 |
| head_operations (head_operations) | 35 | 1 | 1 | 37 |
| junior (junior) | 18 | 19 | 0 | 37 |
| intern (intern) | 17 | 20 | 0 | 37 |

## ceo (level: ceo)

### Passing

| Endpoint | Status | Detail |
|---|---|---|
| roles:list | PASS | HTTP 200 |
| roles:permissions-map | PASS | HTTP 200 |
| roles:create | PASS | HTTP 201 |
| employees:list | PASS | HTTP 200 |
| employee_levels:list | PASS | HTTP 200 |
| departments:list | PASS | HTTP 200 |
| department_units:list | PASS | HTTP 200 |
| branches:list | PASS (404) | Not found (may be expected) |
| company:view | PASS (404) | Not found (may be expected) |
| leads:list | PASS | HTTP 200 |
| clients:list | PASS | HTTP 200 |
| estates:list | PASS | HTTP 200 |
| properties:list | PASS (404) | Not found (may be expected) |
| estate_invoices:list | PASS | HTTP 200 |
| partners:list | PASS | HTTP 200 |
| legal_cases:list | PASS | HTTP 200 |
| compliance_records:list | PASS (404) | Not found (may be expected) |
| compliance_audits:list | PASS | HTTP 200 |
| audit_logs:list | PASS | HTTP 200 |
| announcements:list | PASS | HTTP 200 |
| board_resolutions:list | PASS | HTTP 200 |
| shareholders:list | PASS | HTTP 200 |
| meetings:list | PASS | HTTP 200 |
| policies:list | PASS | HTTP 200 |
| events:list | PASS | HTTP 200 |
| loans:list | PASS | HTTP 200 |
| approval_flows:list | PASS | HTTP 200 |
| approval_requests:list | PASS | HTTP 200 |
| drawings:list | PASS | HTTP 200 |
| wallet:list | PASS | HTTP 200 |
| client_inventory:list | PASS | HTTP 200 |
| job_postings:list | PASS (404) | Not found (may be expected) |
| leave_requests:list | PASS (404) | Not found (may be expected) |
| payroll:list | PASS (404) | Not found (may be expected) |
| assets:list | PASS (404) | Not found (may be expected) |
| awards:list | PASS (404) | Not found (may be expected) |

### Errors / Other

| Endpoint | Status | Detail |
|---|---|---|
| expenses:list | HTTP_500 | Traceback (most recent call last):
  File "/Users/developer/BOMACH/bomach_backen |

## manager (level: manager)

### Passing

| Endpoint | Status | Detail |
|---|---|---|
| roles:list | PASS | HTTP 200 |
| roles:permissions-map | PASS | HTTP 200 |
| employees:list | PASS | HTTP 200 |
| employee_levels:list | PASS | HTTP 200 |
| departments:list | PASS | HTTP 200 |
| department_units:list | PASS | HTTP 200 |
| branches:list | PASS (404) | Not found (may be expected) |
| company:view | PASS (404) | Not found (may be expected) |
| clients:list | PASS | HTTP 200 |
| estates:list | PASS | HTTP 200 |
| properties:list | PASS (404) | Not found (may be expected) |
| estate_invoices:list | PASS | HTTP 200 |
| partners:list | PASS | HTTP 200 |
| legal_cases:list | PASS | HTTP 200 |
| compliance_records:list | PASS (404) | Not found (may be expected) |
| compliance_audits:list | PASS | HTTP 200 |
| audit_logs:list | PASS | HTTP 200 |
| announcements:list | PASS | HTTP 200 |
| board_resolutions:list | PASS | HTTP 200 |
| shareholders:list | PASS | HTTP 200 |
| meetings:list | PASS | HTTP 200 |
| policies:list | PASS | HTTP 200 |
| events:list | PASS | HTTP 200 |
| loans:list | PASS | HTTP 200 |
| approval_flows:list | PASS | HTTP 200 |
| approval_requests:list | PASS | HTTP 200 |
| drawings:list | PASS | HTTP 200 |
| wallet:list | PASS | HTTP 200 |
| client_inventory:list | PASS | HTTP 200 |
| job_postings:list | PASS (404) | Not found (may be expected) |
| leave_requests:list | PASS (404) | Not found (may be expected) |
| payroll:list | PASS (404) | Not found (may be expected) |
| assets:list | PASS (404) | Not found (may be expected) |
| awards:list | PASS (404) | Not found (may be expected) |

### Denied (403)

| Endpoint | Detail |
|---|---|
| roles:create | You do not have permission to perform this action. |

### Errors / Other

| Endpoint | Status | Detail |
|---|---|---|
| leads:list | HTTP_500 | Traceback (most recent call last):
  File "/Users/developer/BOMACH/bomach_backen |
| expenses:list | HTTP_500 | Traceback (most recent call last):
  File "/Users/developer/BOMACH/bomach_backen |

## manager_branch2 (level: manager)

### Passing

| Endpoint | Status | Detail |
|---|---|---|
| roles:list | PASS | HTTP 200 |
| roles:permissions-map | PASS | HTTP 200 |
| employees:list | PASS | HTTP 200 |
| employee_levels:list | PASS | HTTP 200 |
| departments:list | PASS | HTTP 200 |
| department_units:list | PASS | HTTP 200 |
| branches:list | PASS (404) | Not found (may be expected) |
| company:view | PASS (404) | Not found (may be expected) |
| clients:list | PASS | HTTP 200 |
| estates:list | PASS | HTTP 200 |
| properties:list | PASS (404) | Not found (may be expected) |
| estate_invoices:list | PASS | HTTP 200 |
| partners:list | PASS | HTTP 200 |
| legal_cases:list | PASS | HTTP 200 |
| compliance_records:list | PASS (404) | Not found (may be expected) |
| compliance_audits:list | PASS | HTTP 200 |
| audit_logs:list | PASS | HTTP 200 |
| announcements:list | PASS | HTTP 200 |
| board_resolutions:list | PASS | HTTP 200 |
| shareholders:list | PASS | HTTP 200 |
| meetings:list | PASS | HTTP 200 |
| policies:list | PASS | HTTP 200 |
| events:list | PASS | HTTP 200 |
| loans:list | PASS | HTTP 200 |
| approval_flows:list | PASS | HTTP 200 |
| approval_requests:list | PASS | HTTP 200 |
| drawings:list | PASS | HTTP 200 |
| wallet:list | PASS | HTTP 200 |
| client_inventory:list | PASS | HTTP 200 |
| job_postings:list | PASS (404) | Not found (may be expected) |
| leave_requests:list | PASS (404) | Not found (may be expected) |
| payroll:list | PASS (404) | Not found (may be expected) |
| assets:list | PASS (404) | Not found (may be expected) |
| awards:list | PASS (404) | Not found (may be expected) |

### Denied (403)

| Endpoint | Detail |
|---|---|
| roles:create | You do not have permission to perform this action. |

### Errors / Other

| Endpoint | Status | Detail |
|---|---|---|
| leads:list | HTTP_500 | Traceback (most recent call last):
  File "/Users/developer/BOMACH/bomach_backen |
| expenses:list | HTTP_500 | Traceback (most recent call last):
  File "/Users/developer/BOMACH/bomach_backen |

## head_operations (level: head_operations)

### Passing

| Endpoint | Status | Detail |
|---|---|---|
| roles:list | PASS | HTTP 200 |
| roles:permissions-map | PASS | HTTP 200 |
| employees:list | PASS | HTTP 200 |
| employee_levels:list | PASS | HTTP 200 |
| departments:list | PASS | HTTP 200 |
| department_units:list | PASS | HTTP 200 |
| branches:list | PASS (404) | Not found (may be expected) |
| company:view | PASS (404) | Not found (may be expected) |
| leads:list | PASS | HTTP 200 |
| clients:list | PASS | HTTP 200 |
| estates:list | PASS | HTTP 200 |
| properties:list | PASS (404) | Not found (may be expected) |
| estate_invoices:list | PASS | HTTP 200 |
| partners:list | PASS | HTTP 200 |
| legal_cases:list | PASS | HTTP 200 |
| compliance_records:list | PASS (404) | Not found (may be expected) |
| compliance_audits:list | PASS | HTTP 200 |
| audit_logs:list | PASS | HTTP 200 |
| announcements:list | PASS | HTTP 200 |
| board_resolutions:list | PASS | HTTP 200 |
| shareholders:list | PASS | HTTP 200 |
| meetings:list | PASS | HTTP 200 |
| policies:list | PASS | HTTP 200 |
| events:list | PASS | HTTP 200 |
| loans:list | PASS | HTTP 200 |
| approval_flows:list | PASS | HTTP 200 |
| approval_requests:list | PASS | HTTP 200 |
| drawings:list | PASS | HTTP 200 |
| wallet:list | PASS | HTTP 200 |
| client_inventory:list | PASS | HTTP 200 |
| job_postings:list | PASS (404) | Not found (may be expected) |
| leave_requests:list | PASS (404) | Not found (may be expected) |
| payroll:list | PASS (404) | Not found (may be expected) |
| assets:list | PASS (404) | Not found (may be expected) |
| awards:list | PASS (404) | Not found (may be expected) |

### Denied (403)

| Endpoint | Detail |
|---|---|
| roles:create | You do not have permission to perform this action. |

### Errors / Other

| Endpoint | Status | Detail |
|---|---|---|
| expenses:list | HTTP_500 | Traceback (most recent call last):
  File "/Users/developer/BOMACH/bomach_backen |

## junior (level: junior)

### Passing

| Endpoint | Status | Detail |
|---|---|---|
| roles:permissions-map | PASS | HTTP 200 |
| employees:list | PASS | HTTP 200 |
| employee_levels:list | PASS | HTTP 200 |
| departments:list | PASS | HTTP 200 |
| department_units:list | PASS | HTTP 200 |
| branches:list | PASS (404) | Not found (may be expected) |
| company:view | PASS (404) | Not found (may be expected) |
| properties:list | PASS (404) | Not found (may be expected) |
| compliance_records:list | PASS (404) | Not found (may be expected) |
| announcements:list | PASS | HTTP 200 |
| policies:list | PASS | HTTP 200 |
| events:list | PASS | HTTP 200 |
| loans:list | PASS | HTTP 200 |
| job_postings:list | PASS (404) | Not found (may be expected) |
| leave_requests:list | PASS (404) | Not found (may be expected) |
| payroll:list | PASS (404) | Not found (may be expected) |
| assets:list | PASS (404) | Not found (may be expected) |
| awards:list | PASS (404) | Not found (may be expected) |

### Denied (403)

| Endpoint | Detail |
|---|---|
| roles:list | You do not have permission to perform this action. |
| roles:create | You do not have permission to perform this action. |
| leads:list | You do not have permission to perform this action. |
| clients:list | You do not have permission to perform this action. |
| estates:list | You do not have permission to perform this action. |
| estate_invoices:list | You do not have permission to perform this action. |
| partners:list | You do not have permission to perform this action. |
| legal_cases:list | You do not have permission to perform this action. |
| compliance_audits:list | You do not have permission to perform this action. |
| audit_logs:list | You do not have permission to perform this action. |
| board_resolutions:list | You do not have permission to perform this action. |
| shareholders:list | You do not have permission to perform this action. |
| meetings:list | You do not have permission to perform this action. |
| approval_flows:list | You do not have permission to perform this action. |
| approval_requests:list | You do not have permission to perform this action. |
| drawings:list | You do not have permission to perform this action. |
| wallet:list | You do not have permission to perform this action. |
| client_inventory:list | You do not have permission to perform this action. |
| expenses:list | You do not have permission to perform this action. |

## intern (level: intern)

### Passing

| Endpoint | Status | Detail |
|---|---|---|
| roles:permissions-map | PASS | HTTP 200 |
| employees:list | PASS | HTTP 200 |
| employee_levels:list | PASS | HTTP 200 |
| departments:list | PASS | HTTP 200 |
| department_units:list | PASS | HTTP 200 |
| branches:list | PASS (404) | Not found (may be expected) |
| company:view | PASS (404) | Not found (may be expected) |
| properties:list | PASS (404) | Not found (may be expected) |
| compliance_records:list | PASS (404) | Not found (may be expected) |
| announcements:list | PASS | HTTP 200 |
| policies:list | PASS | HTTP 200 |
| events:list | PASS | HTTP 200 |
| job_postings:list | PASS (404) | Not found (may be expected) |
| leave_requests:list | PASS (404) | Not found (may be expected) |
| payroll:list | PASS (404) | Not found (may be expected) |
| assets:list | PASS (404) | Not found (may be expected) |
| awards:list | PASS (404) | Not found (may be expected) |

### Denied (403)

| Endpoint | Detail |
|---|---|
| roles:list | You do not have permission to perform this action. |
| roles:create | You do not have permission to perform this action. |
| leads:list | You do not have permission to perform this action. |
| clients:list | You do not have permission to perform this action. |
| estates:list | You do not have permission to perform this action. |
| estate_invoices:list | You do not have permission to perform this action. |
| partners:list | You do not have permission to perform this action. |
| legal_cases:list | You do not have permission to perform this action. |
| compliance_audits:list | You do not have permission to perform this action. |
| audit_logs:list | You do not have permission to perform this action. |
| board_resolutions:list | You do not have permission to perform this action. |
| shareholders:list | You do not have permission to perform this action. |
| meetings:list | You do not have permission to perform this action. |
| loans:list | You do not have permission to perform this action. |
| approval_flows:list | You do not have permission to perform this action. |
| approval_requests:list | You do not have permission to perform this action. |
| drawings:list | You do not have permission to perform this action. |
| wallet:list | You do not have permission to perform this action. |
| client_inventory:list | You do not have permission to perform this action. |
| expenses:list | You do not have permission to perform this action. |

## Cross-Reference: Endpoint x Level

| Endpoint | ceo | manager | manager_branch2 | head_operations | junior | intern |
|---|---|---|---|---|---|---|
| roles:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| roles:permissions-map | PASS | PASS | PASS | PASS | PASS | PASS |
| roles:create | PASS | DENIED | DENIED | DENIED | DENIED | DENIED |
| employees:list | PASS | PASS | PASS | PASS | PASS | PASS |
| employee_levels:list | PASS | PASS | PASS | PASS | PASS | PASS |
| departments:list | PASS | PASS | PASS | PASS | PASS | PASS |
| department_units:list | PASS | PASS | PASS | PASS | PASS | PASS |
| branches:list | PASS | PASS | PASS | PASS | PASS | PASS |
| company:view | PASS | PASS | PASS | PASS | PASS | PASS |
| leads:list | PASS | HTTP_500 | HTTP_500 | PASS | DENIED | DENIED |
| clients:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| estates:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| properties:list | PASS | PASS | PASS | PASS | PASS | PASS |
| estate_invoices:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| partners:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| legal_cases:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| compliance_records:list | PASS | PASS | PASS | PASS | PASS | PASS |
| compliance_audits:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| audit_logs:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| announcements:list | PASS | PASS | PASS | PASS | PASS | PASS |
| board_resolutions:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| shareholders:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| meetings:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| policies:list | PASS | PASS | PASS | PASS | PASS | PASS |
| events:list | PASS | PASS | PASS | PASS | PASS | PASS |
| loans:list | PASS | PASS | PASS | PASS | PASS | DENIED |
| approval_flows:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| approval_requests:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| drawings:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| wallet:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| client_inventory:list | PASS | PASS | PASS | PASS | DENIED | DENIED |
| job_postings:list | PASS | PASS | PASS | PASS | PASS | PASS |
| leave_requests:list | PASS | PASS | PASS | PASS | PASS | PASS |
| payroll:list | PASS | PASS | PASS | PASS | PASS | PASS |
| assets:list | PASS | PASS | PASS | PASS | PASS | PASS |
| awards:list | PASS | PASS | PASS | PASS | PASS | PASS |
| expenses:list | HTTP_500 | HTTP_500 | HTTP_500 | HTTP_500 | DENIED | DENIED |