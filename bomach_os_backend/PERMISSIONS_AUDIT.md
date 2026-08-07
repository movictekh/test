# BOMACH Backend — Permissions Audit

## Employee Model Fields Available for Permission Checks

| Field | Type | Description |
|-------|------|-------------|
| `level` | FK → EmployeeLevel | Employee seniority level (intern → CEO) |
| `branch` | FK → Branch | Which branch the employee works at |
| `department` | FK → Department | Which department (Operations, Marketing, Finance, IT, HR, Legal) |
| `department_unit` | FK → Unit | Sub-unit within the department |
| `reporting_to` | FK → Employee (self) | The employee's direct manager |
| `employment_type` | CharField | full-time, part-time, intern, contract, freelance, *-associate |
| `employment_status` | CharField | active, on-probation, on-leave, suspended, terminated |
| `designation` | CharField | Job title |


## Current Permission Utility (`user/utils/perm.py`)

- `check_strength(level, required)` — returns True if `level >= required`
- `owns_or_above(owns, employee_level, least_required_level, incharge_of_section)` — allows if user owns the record OR has the required level + is in charge
- `show_list_queryset(incharge_of, full_queryset, personal_queryset)` — returns full or filtered queryset based on role

---

## Endpoint Audit by Module

### USER MODULE (`user/api/v1/`)

#### auth.py — Authentication
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| POST | `/auth/login` | N/A | auth=None | Public — correct |
| POST | `/auth/logout` | auth only | — | Correct |
| POST | `/auth/refresh` | N/A | auth=None | Public — correct |
| POST | `/auth/forgot-password` | N/A | auth=None | Public — correct |
| POST | `/auth/reset-password` | N/A | auth=None | Public — correct |
| GET | `/auth/me` | auth only | — | Correct |
| GET | `/auth/verify-token` | auth only | — | Correct |

#### employee.py — Employee Management
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| POST | `/employees/` | YES | HEAD | Create employee |
| GET | `/employees/` | YES | HEAD or owns | List — scoped by level |
| GET | `/employees/{id}` | YES | HEAD or owns | |
| PUT | `/employees/{id}` | YES | HEAD or owns | |
| POST | `/employees/exit/{id}` | YES | MANAGER | Offboard employee |
| POST | `/employees/{id}/documents` | YES | MANAGER or owns | |
| GET | `/employees/{id}/documents` | YES | HEAD or owns | |
| DELETE | `/employees/{id}/documents/{doc_id}` | YES | MANAGER | |
| POST | `/employees/{id}/reviews` | YES | MANAGER | |
| GET | `/employees/{id}/reviews` | YES | HEAD or owns | |
| PUT | `/employees/reviews/{id}` | YES | MANAGER or reviewer | |
| DELETE | `/employees/reviews/{id}` | YES | MANAGER or reviewer | |
| GET | `/employees/employee-levels` | NO | — | Read-only choices — OK |
| GET | `/employees/department` | NO | — | Read-only choices — OK |
| POST | `/employees/department` | YES | MANAGER | |
| PUT | `/employees/department/{id}` | YES | MANAGER | |
| GET | `/employees/unit` | NO | — | Read-only choices — OK |
| POST | `/employees/unit` | YES | MANAGER | |
| PUT | `/employees/unit/{id}` | YES | MANAGER | |

#### role.py — Role Management
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| POST | `/roles/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/roles/` | **NO** | — | **MISSING — needs auth scoping** |
| GET | `/roles/{id}` | **NO** | — | **MISSING** |
| PUT | `/roles/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/roles/{id}` | **NO** | — | **MISSING — needs CEO** |

#### branch.py — Branch Management
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/branch/countries` | NO | — | Read-only — OK |
| GET | `/branch/countries/{id}` | NO | — | Read-only — OK |
| GET | `/branch/states` | NO | — | Read-only — OK |
| GET | `/branch/states/{id}` | NO | — | Read-only — OK |
| GET | `/branch/branches` | NO | — | Read-only — OK |
| GET | `/branch/branches/{id}` | NO | — | Read-only — OK |
| POST | `/branch/branches` | YES | CEO | |
| PUT | `/branch/branches/{id}` | YES | CEO | |
| GET | `/branch/branches/{id}/business-hours` | NO | — | Read-only — OK |
| PUT | `/branch/branches/{id}/business-hours` | YES | CEO | |
| GET | `/branch/branches/choices/fields` | NO | — | Read-only — OK |
| GET | `/branch/branches/{id}/performance` | NO | — | Read-only — OK |

#### company.py — Company Settings
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/company/company-settings` | NO | — | Read-only — OK |
| PUT | `/company/company-settings` | YES | CEO | |

#### clients.py — Leads & Clients
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/clients/leads/` | YES | MID_LEVEL | Scoped by assignment |
| GET | `/clients/leads/{id}` | auth only | — | OK |
| POST | `/clients/leads/` | YES | MID_LEVEL | |
| PUT | `/clients/leads/{id}` | YES | MID_LEVEL | |
| DELETE | `/clients/leads/{id}` | YES | MANAGER | |
| GET | `/clients/clients/` | auth only | — | OK |
| GET | `/clients/clients/{id}` | auth only | — | OK |
| POST | `/clients/clients/` | YES | MID_LEVEL | |
| PUT | `/clients/clients/{id}` | YES | MID_LEVEL | |
| POST | `/clients/leads/{id}/convert-to-client` | YES | MID_LEVEL | |

#### estate.py — Real Estate
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/estates/choices/fields` | NO | — | Read-only — OK |
| GET | `/estates/` | NO | — | Read-only — OK |
| GET | `/estates/{id}` | NO | — | Read-only — OK |
| POST | `/estates/` | YES | MANAGER | |
| PUT | `/estates/{id}` | YES | MANAGER | |
| DELETE | `/estates/{id}` | YES | CEO | |
| GET | `/estates/{id}/properties/choices/fields` | NO | — | Read-only — OK |
| GET | `/estates/{id}/properties` | NO | — | Read-only — OK |
| GET | `/estates/{id}/properties/{pid}` | NO | — | Read-only — OK |
| POST | `/estates/{id}/properties` | YES | MANAGER | |
| PUT | `/estates/{id}/properties/{pid}` | YES | MANAGER | |
| DELETE | `/estates/{id}/properties/{pid}` | YES | CEO | |
| GET | `/estates/properties/all` | NO | — | Read-only — OK |
| GET | `/estates/properties/all/{id}` | NO | — | Read-only — OK |
| POST | `/estates/properties/all` | YES | MANAGER | |
| PUT | `/estates/properties/all/{id}` | YES | MANAGER | |
| DELETE | `/estates/properties/all/{id}` | YES | CEO | |

#### estate_property_invoice.py — Estate Invoices
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/estate-invoices/choices/fields` | NO | — | Read-only — OK |
| GET | `/estate-invoices/` | NO | — | Read-only — OK |
| GET | `/estate-invoices/pending-approvals` | NO | — | Scoped to user — OK |
| GET | `/estate-invoices/{id}` | NO | — | Read-only — OK |
| POST | `/estate-invoices/` | YES | MID_LEVEL | |
| PUT | `/estate-invoices/{id}` | YES | MID_LEVEL | |
| DELETE | `/estate-invoices/{id}` | YES | MID_LEVEL | |
| POST | `/estate-invoices/{id}/submit-for-approval` | NO | — | **MISSING — needs MID_LEVEL+** |
| POST | `/estate-invoices/{id}/approvals/{step}/decide` | YES | assigned_to or level | |
| POST | `/estate-invoices/{id}/record-payment` | **NO** | — | **MISSING — needs MANAGER+** |

#### cart.py — Shopping Cart
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/cart/` | **NO** | — | Scoped to user — OK |
| POST | `/cart/items` | **NO** | — | Scoped to user — OK |
| DELETE | `/cart/items/{id}` | **NO** | — | **MISSING — should verify ownership** |
| DELETE | `/cart/items/property/{id}` | **NO** | — | **MISSING — should verify ownership** |
| DELETE | `/cart/clear` | **NO** | — | **MISSING — should verify ownership** |
| GET | `/cart/count` | **NO** | — | Scoped to user — OK |

#### cases.py — Legal Cases
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/cases/` | auth only | — | OK |
| GET | `/cases/statistics/overview/` | auth only | — | OK |
| GET | `/cases/upcoming-hearings/` | auth only | — | OK |
| GET | `/cases/{id}` | auth only | — | OK |
| POST | `/cases/` | YES | MANAGER | |
| PUT | `/cases/{id}` | YES | MANAGER | |
| PATCH | `/cases/{id}/status` | YES | MANAGER | |
| DELETE | `/cases/{id}` | YES | CEO | |

#### compliance.py — Compliance Records
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/compliance/compliance-records` | NO | — | Read-only — OK |
| GET | `/compliance/compliance-records/{id}` | NO | — | Read-only — OK |
| POST | `/compliance/compliance-records` | YES | MANAGER | |
| PUT | `/compliance/compliance-records/{id}` | YES | MANAGER | |

#### audit.py — Compliance Audits
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/audits/` | NO | — | Read-only — OK |
| GET | `/audits/statistics/overview/` | NO | — | Read-only — OK |
| GET | `/audits/statistics/performance-trends/` | NO | — | Read-only — OK |
| GET | `/audits/failing-audits/` | NO | — | Read-only — OK |
| GET | `/audits/auditors/` | NO | — | Read-only — OK |
| GET | `/audits/{id}` | NO | — | Read-only — OK |
| POST | `/audits/` | YES | MANAGER | |
| PUT | `/audits/{id}` | YES | MANAGER | |
| PATCH | `/audits/{id}/status` | YES | MANAGER | |
| PATCH | `/audits/{id}/score` | YES | MANAGER | |
| DELETE | `/audits/{id}` | YES | CEO | |

#### audit_log.py — Audit Logs
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/audit-logs/` | YES | MANAGER | |

#### announcement.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/announcements/choices` | NO | auth=None | Read-only — OK |
| GET | `/announcements/` | NO | — | Read-only — OK |
| GET | `/announcements/{id}` | NO | — | Read-only — OK |
| POST | `/announcements/` | YES | MANAGER | |
| PUT | `/announcements/{id}` | YES | MANAGER | |
| DELETE | `/announcements/{id}` | YES | MANAGER | |

#### approval.py — Approval Flows
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/approvals/flows/choices` | NO | auth=None | Read-only — OK |
| GET | `/approvals/flows` | NO | — | Read-only — OK |
| GET | `/approvals/flows/{id}` | NO | — | Read-only — OK |
| POST | `/approvals/flows` | YES | HEAD | |
| PUT | `/approvals/flows/{id}` | YES | HEAD | |
| DELETE | `/approvals/flows/{id}` | YES | HEAD | |
| GET | `/approvals/requests` | NO | — | Scoped by level — OK |
| GET | `/approvals/requests/{id}` | NO | — | Read-only — OK |
| POST | `/approvals/requests` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| POST | `/approvals/requests/{id}/approve` | YES | level-based | |
| POST | `/approvals/requests/{id}/reject` | YES | level-based | |
| DELETE | `/approvals/requests/{id}` | YES | creator or HEAD+ | |

#### board_resolution.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/board-resolutions/choices` | NO | auth=None | Read-only — OK |
| GET | `/board-resolutions/` | NO | — | Read-only — OK |
| GET | `/board-resolutions/{id}` | NO | — | Read-only — OK |
| POST | `/board-resolutions/` | YES | MANAGER | |
| PUT | `/board-resolutions/{id}` | YES | MANAGER | |
| POST | `/board-resolutions/{id}/approve` | YES | CEO | |
| DELETE | `/board-resolutions/{id}` | YES | MANAGER | |

#### shareholder.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/shareholders/` | NO | — | Read-only — OK |
| GET | `/shareholders/{id}` | NO | — | Read-only — OK |
| POST | `/shareholders/` | YES | HEAD | |
| PUT | `/shareholders/{id}` | YES | HEAD | |
| DELETE | `/shareholders/{id}` | YES | HEAD | |

#### meeting.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/meetings/` | NO | — | Read-only — OK |
| GET | `/meetings/{id}` | NO | — | Read-only — OK |
| POST | `/meetings/` | YES | MANAGER | |
| PUT | `/meetings/{id}` | YES | MANAGER | |
| DELETE | `/meetings/{id}` | YES | MANAGER | |

#### policy.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/policies/` | NO | — | Read-only — OK |
| GET | `/policies/{id}` | NO | — | Read-only — OK |
| POST | `/policies/` | YES | MANAGER | |
| PUT | `/policies/{id}` | YES | MANAGER | |
| DELETE | `/policies/{id}` | YES | MANAGER | |

#### event.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/events/` | NO | — | Read-only — OK |
| GET | `/events/{id}` | NO | — | Read-only — OK |
| POST | `/events/` | YES | MANAGER | |
| PUT | `/events/{id}` | YES | MANAGER | |
| DELETE | `/events/{id}` | YES | MANAGER | |

#### loan.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/loans/` | NO | — | Read-only — OK |
| GET | `/loans/{id}` | NO | — | Read-only — OK |
| POST | `/loans/` | YES | MANAGER | |
| PUT | `/loans/{id}` | YES | MANAGER | |
| DELETE | `/loans/{id}` | YES | MANAGER | |

#### wallet.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/wallet/` | auth only | — | Scoped to user — OK |
| POST | `/wallet/fund` | auth only | — | Scoped to user — OK |

#### client_inventory.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/inventory/` | NO | — | Read-only — OK |
| GET | `/inventory/{id}` | NO | — | Read-only — OK |
| POST | `/inventory/` | YES | MANAGER | |
| PUT | `/inventory/{id}` | YES | MANAGER | |
| DELETE | `/inventory/{id}` | YES | MANAGER | |

#### drawing_bank.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/drawing-bank/stats` | NO | — | Read-only — OK |
| GET | `/drawing-bank/` | NO | — | Scoped to user — OK |
| GET | `/drawing-bank/{id}` | NO | — | Ownership check — OK |
| POST | `/drawing-bank/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| PUT | `/drawing-bank/{id}` | **NO** | — | **MISSING — needs ownership or MID_LEVEL+** |
| DELETE | `/drawing-bank/{id}` | **NO** | — | **MISSING — needs ownership or MANAGER+** |
| POST | `/drawing-bank/{id}/approve` | YES | MANAGER | |
| POST | `/drawing-bank/{id}/reject` | YES | MANAGER | |
| POST | `/drawing-bank/{id}/download` | **NO** | — | **MISSING — needs auth check** |

#### partner.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/partners/choices/fields` | NO | — | Read-only — OK |
| GET | `/partners/` | NO | — | Read-only — OK |
| GET | `/partners/{id}` | NO | — | Read-only — OK |
| POST | `/partners/` | YES | CEO | |
| PUT | `/partners/{id}` | YES | CEO | |
| DELETE | `/partners/{id}` | YES | CEO | |
| GET | `/partners/{id}/agreements` | NO | — | Read-only — OK |
| GET | `/partners/{id}/agreements/{aid}` | NO | — | Read-only — OK |
| POST | `/partners/{id}/agreements` | YES | CEO | |
| PUT | `/partners/{id}/agreements/{aid}` | YES | CEO | |
| DELETE | `/partners/{id}/agreements/{aid}` | YES | CEO | |

#### dashboard.py — Employee Dashboard
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/dashboard/summary` | **NO** | — | **Should scope data to user's level** |
| GET | `/dashboard/performance-card` | **NO** | — | **Should scope data to user** |

#### stats.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/stats/` | **NO** | — | **MISSING — sensitive aggregate data, needs MANAGER+** |

---

### SERVICES MODULE (`services/api/v1/`)

**ALL endpoints in services have NO permission checks. Every authenticated user can CRUD everything.**

#### budgets.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/budgets/` | **NO** | — | **MISSING** |
| POST | `/budgets/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/budgets/{id}` | **NO** | — | **MISSING** |
| PUT | `/budgets/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/budgets/{id}` | **NO** | — | **MISSING — needs CEO** |

#### categories.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/categories/` | **NO** | — | Read-only — OK |
| POST | `/categories/` | **NO** | — | **MISSING — needs MANAGER+** |
| PUT | `/categories/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/categories/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### content.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/content/` | **NO** | — | Read-only — OK |
| POST | `/content/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| PUT | `/content/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/content/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### documents.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/documents/` | **NO** | — | Read-only — OK |
| POST | `/documents/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| GET | `/documents/{id}` | **NO** | — | Read-only — OK |
| PUT | `/documents/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/documents/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### expenses.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/expenses/` | **NO** | — | **MISSING — sensitive financial data** |
| POST | `/expenses/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| GET | `/expenses/{id}` | **NO** | — | **MISSING** |
| PUT | `/expenses/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/expenses/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### invoices.py (services)
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/invoices/` | **NO** | — | **MISSING — sensitive** |
| POST | `/invoices/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| GET | `/invoices/{id}` | **NO** | — | **MISSING** |
| PUT | `/invoices/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/invoices/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### leads.py (services)
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/leads/` | **NO** | — | **MISSING** |
| POST | `/leads/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| GET | `/leads/{id}` | **NO** | — | **MISSING** |
| PUT | `/leads/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/leads/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### marketing_campaigns.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/marketing-campaigns/` | **NO** | — | Read-only — OK |
| POST | `/marketing-campaigns/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/marketing-campaigns/{id}` | **NO** | — | Read-only — OK |
| PUT | `/marketing-campaigns/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/marketing-campaigns/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### orders.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/orders/` | **NO** | — | **MISSING** |
| POST | `/orders/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| GET | `/orders/{id}` | **NO** | — | **MISSING** |
| PUT | `/orders/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/orders/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### payments.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/payments/` | **NO** | — | **MISSING — sensitive financial** |
| POST | `/payments/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/payments/{id}` | **NO** | — | **MISSING** |
| PUT | `/payments/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/payments/{id}` | **NO** | — | **MISSING — needs CEO** |

#### property.py (services)
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/properties/stats` | **NO** | — | Read-only — OK |
| GET | `/properties/` | **NO** | — | Read-only — OK |
| GET | `/properties/{id}` | **NO** | — | Read-only — OK |
| POST | `/properties/` | **NO** | — | **MISSING — needs MANAGER+** |
| PUT | `/properties/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/properties/{id}` | **NO** | — | **MISSING — needs CEO** |

#### quotes.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/quotes/` | **NO** | — | **MISSING** |
| POST | `/quotes/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| GET | `/quotes/{id}` | **NO** | — | **MISSING** |
| PUT | `/quotes/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/quotes/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### services.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/services/` | **NO** | — | Read-only — OK |
| POST | `/services/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/services/{id}` | **NO** | — | Read-only — OK |
| PUT | `/services/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/services/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### stats.py (services)
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/stats/` | **NO** | — | **MISSING — sensitive aggregate data** |

---

### OPERATIONS MODULE (`operations/api/v1/`)

**ALL endpoints in operations have NO permission checks.**

#### projects.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/projects/` | **NO** | — | Read-only — OK |
| GET | `/projects/stats` | **NO** | — | Read-only — OK |
| GET | `/projects/{id}` | **NO** | — | Read-only — OK |
| GET | `/projects/{id}/employees` | **NO** | — | Read-only — OK |
| POST | `/projects/` | **NO** | — | **MISSING — needs MANAGER+** |
| PUT | `/projects/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/projects/{id}` | **NO** | — | **MISSING — needs CEO** |

#### tasks.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/tasks/` | **NO** | — | Read-only — OK |
| POST | `/tasks/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| GET | `/tasks/{id}` | **NO** | — | Read-only — OK |
| PUT | `/tasks/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/tasks/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### worksites.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/worksites/` | **NO** | — | Read-only — OK |
| POST | `/worksites/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/worksites/{id}` | **NO** | — | Read-only — OK |
| PUT | `/worksites/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/worksites/{id}` | **NO** | — | **MISSING — needs CEO** |

#### contracts.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/contracts/` | **NO** | — | Read-only — OK |
| POST | `/contracts/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/contracts/{id}` | **NO** | — | Read-only — OK |
| PUT | `/contracts/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/contracts/{id}` | **NO** | — | **MISSING — needs CEO** |

#### timelines.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/timelines/` | **NO** | — | Read-only — OK |
| POST | `/timelines/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| GET | `/timelines/{id}` | **NO** | — | Read-only — OK |
| PUT | `/timelines/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/timelines/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### milestones.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/milestones/` | **NO** | — | Read-only — OK |
| POST | `/milestones/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| GET | `/milestones/{id}` | **NO** | — | Read-only — OK |
| PUT | `/milestones/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/milestones/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### site_equipment.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/site-equipment/` | **NO** | — | Read-only — OK |
| POST | `/site-equipment/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| GET | `/site-equipment/{id}` | **NO** | — | Read-only — OK |
| PUT | `/site-equipment/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/site-equipment/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### dashboard.py (operations)
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/dashboard/` | **NO** | — | Read-only — OK |

---

### HR MODULE (`hr/api/v1/`)

#### dashboard.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/dashboard/` | **NO** | — | **MISSING — HR data, needs HEAD+** |

#### job_postings.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/job-postings/` | **NO** | — | Read-only — OK |
| POST | `/job-postings/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/job-postings/{id}` | **NO** | — | Read-only — OK |
| PUT | `/job-postings/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/job-postings/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### applicants.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/applicants/` | **NO** | — | **MISSING — needs HEAD+** |
| POST | `/applicants/` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| GET | `/applicants/{id}` | **NO** | — | **MISSING** |
| PUT | `/applicants/{id}` | **NO** | — | **MISSING — needs MID_LEVEL+** |
| DELETE | `/applicants/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### leave_requests.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/leave-requests/` | **NO** | — | **Should scope to user or manager** |
| POST | `/leave-requests/` | **NO** | — | Scoped to user — OK |
| GET | `/leave-requests/{id}` | **NO** | — | **Should scope to user or manager** |
| PUT | `/leave-requests/{id}` | **NO** | — | **MISSING — needs ownership check** |
| POST | `/leave-requests/{id}/approve` | **NO** | — | **MISSING — needs MANAGER+** |
| POST | `/leave-requests/{id}/reject` | **NO** | — | **MISSING — needs MANAGER+** |

#### payroll.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/payroll/` | **NO** | — | **MISSING — sensitive, needs MANAGER+** |
| POST | `/payroll/process-batch` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/payroll/make-payment/{year}/{month}` | YES | MANAGER | |
| POST | `/payroll/make-payment/{year}/{month}/authorize` | YES | MANAGER | |

#### performance_reviews.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/performance-reviews/` | **NO** | — | **MISSING — needs HEAD+ or own** |
| POST | `/performance-reviews/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/performance-reviews/{id}` | **NO** | — | **MISSING** |
| PUT | `/performance-reviews/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/performance-reviews/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### training_programs.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/training-programs/` | **NO** | — | Read-only — OK |
| POST | `/training-programs/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/training-programs/{id}` | **NO** | — | Read-only — OK |
| PUT | `/training-programs/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/training-programs/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### assets.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/assets/` | **NO** | — | Read-only — OK |
| POST | `/assets/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/assets/{id}` | **NO** | — | Read-only — OK |
| PUT | `/assets/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/assets/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### award.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/awards/` | **NO** | — | Read-only — OK |
| POST | `/awards/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/awards/{id}` | **NO** | — | Read-only — OK |
| PUT | `/awards/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/awards/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### work_reports.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/work-reports/` | **NO** | — | **Should scope to user/manager** |
| POST | `/work-reports/` | **NO** | — | Scoped to user — OK |
| GET | `/work-reports/{id}` | **NO** | — | **Should scope to user/manager** |
| PUT | `/work-reports/{id}` | **NO** | — | **MISSING — needs ownership** |
| DELETE | `/work-reports/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### disciplinary_cases.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/disciplinary-cases/` | **NO** | — | **MISSING — sensitive, needs MANAGER+** |
| POST | `/disciplinary-cases/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/disciplinary-cases/{id}` | **NO** | — | **MISSING** |
| PUT | `/disciplinary-cases/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/disciplinary-cases/{id}` | **NO** | — | **MISSING — needs CEO** |

#### monthly_scorecards.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/monthly-scorecards/` | **NO** | — | **Should scope to user/manager** |
| POST | `/monthly-scorecards/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/monthly-scorecards/{id}` | **NO** | — | **Should scope** |
| PUT | `/monthly-scorecards/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/monthly-scorecards/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### employee_evaluations.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/employee-evaluations/` | **NO** | — | **MISSING — sensitive, needs HEAD+** |
| POST | `/employee-evaluations/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/employee-evaluations/{id}` | **NO** | — | **MISSING** |
| PUT | `/employee-evaluations/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/employee-evaluations/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### kpis.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/kpis/` | **NO** | — | Read-only — OK |
| POST | `/kpis/` | **NO** | — | **MISSING — needs MANAGER+** |
| GET | `/kpis/{id}` | **NO** | — | Read-only — OK |
| PUT | `/kpis/{id}` | **NO** | — | **MISSING — needs MANAGER+** |
| DELETE | `/kpis/{id}` | **NO** | — | **MISSING — needs MANAGER+** |

#### interviews.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/applicants/{id}/interviews` | **NO** | — | **MISSING — needs HEAD+** |
| POST | `/applicants/{id}/interviews` | **NO** | — | **MISSING — needs MANAGER+** |
| PUT | `/applicants/{id}/interviews/{iid}` | **NO** | — | **MISSING — needs MANAGER+** |

#### offer_letters.py
| Method | Path | Has Perm Check | Required Level | Notes |
|--------|------|:--------------:|----------------|-------|
| GET | `/applicants/{id}/offer-letters` | **NO** | — | **MISSING — needs MANAGER+** |
| POST | `/applicants/{id}/offer-letters` | **NO** | — | **MISSING — needs MANAGER+** |
| PUT | `/applicants/{id}/offer-letters/{oid}` | **NO** | — | **MISSING — needs MANAGER+** |

---

## Summary of Missing Permissions

| Module | Total Endpoints | With Perm Check | Missing | Critical |
|--------|:--------------:|:--------------:|:-------:|:--------:|
| **User** | ~85 | ~55 | ~10 | 5 |
| **Services** | ~55 | 0 | ~35 | 35 |
| **Operations** | ~35 | 0 | ~20 | 20 |
| **HR** | ~45 | 2 | ~35 | 35 |
| **TOTAL** | ~220 | ~57 | ~100 | ~95 |

### Recommended Permission Levels by Action Type

| Action | Recommended Level |
|--------|------------------|
| List/Read (general) | Any authenticated user |
| List/Read (sensitive: payroll, disciplinary, evaluations) | HEAD+ or scoped to own |
| Create | MID_LEVEL+ |
| Update | MID_LEVEL+ or owner |
| Delete | MANAGER+ |
| Delete (destructive/permanent) | CEO |
| Approve/Reject | MANAGER+ or assigned approver |
| Financial operations (payments, budgets) | MANAGER+ |
| System config (branches, company settings) | CEO |

### Possible Additional Permission Dimensions

Beyond level-based checks, consider:

1. **Branch scoping** — employees should only see/edit data for their branch (use `request.user.employee_profile.branch`)
2. **Department scoping** — HR endpoints scoped to HR department, Legal to legal, etc. (use `request.user.employee_profile.department`)
3. **Ownership** — users can always edit their own records (leave requests, work reports, drawing bank submissions)
4. **Reporting chain** — managers can see/approve records for their direct reports (use `reporting_to` field)
5. **Employment status** — suspended/terminated employees should not have write access
