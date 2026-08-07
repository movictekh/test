# Permission System Analysis (Updated)

## What Was Changed

### 1. EmployeeLevel — replaced generic `head` with specific head levels

**Before:** One `head` level for all department heads.
**After:** Six specific levels: `head_hr`, `head_operations`, `head_marketing`, `head_finance`, `head_legal`, `head_it`.

This lets you create roles that target a specific head. E.g. a role with `level=head_hr` only applies to the Head of HR, not the Head of Finance.

### 2. Strength hierarchy (single source of truth)

```
CEO             = 10
C-suite / Board = 9   (cto, cfo, clo, chro, cmo, board_member)
Manager         = 7   (branch manager)
Head of Dept    = 6   (head_hr, head_operations, head_marketing, etc.)
High            = 5
Senior          = 4
Mid Level       = 3
Junior          = 2
Intern          = 1
```

The `STRENGTH` dict now lives on `EmployeeLevel` as a class attribute. Both `user/utils/perm.py` and `hr/utils/perm.py` reference it instead of having their own copies.

### 3. Branch scoping rules (built into EmployeeLevel)

| Level | Scope | How it works |
|-------|-------|--------------|
| Intern → Manager (strength ≤ 7) | **Branch only** | Queryset filtered to `employee.branch` |
| Head of Dept (strength 6) | **Their department, all branches** | Queryset filtered to `employee.department` |
| C-suite / Board (strength ≥ 9) | **Company-wide** | No queryset filter |

These are exposed as properties on `EmployeeLevel`:
- `is_branch_scoped` — True for manager and below
- `is_company_wide` — True for c-suite and board
- `is_head` — True for head_* levels

**Important:** Branch scoping is NOT on the Role model. The Role says **what** you can do. The queryset filter (in the decorator/view) controls **which records** you can see.

### 4. Role model — added `department` FK

The Role model now has three optional scoping fields:
- `level` — match employees at this exact level
- `department` — match employees in this department
- `unit` — match employees in this specific unit

Examples:
```
"All Employees"           → level=None, dept=None, unit=None
"HR Team"                 → level=None, dept=HR, unit=None
"HR Recruitment Unit"     → level=None, dept=None, unit=Recruitment
"Head of HR"              → level=head_hr, dept=None, unit=None
"Branch Manager"          → level=manager, dept=None, unit=None
"CEO"                     → level=ceo, dept=None, unit=None
"Finance Interns"         → level=intern, dept=Finance, unit=None
```

### 5. PERMISSIONS_MAP — added `_own` variants

Resources with personal ownership now have `_own` action variants:
- `view_own`, `list_own`, `update_own`, `delete_own`, `upload_own`

This covers the "employee can see their own leave request" use case without giving them broad `view` access.

---

## Is This Sufficient? (CEO down to Intern)

**Yes.** Here's how every level gets permissions:

| Level | How they get permissions | Example |
|-------|------------------------|---------|
| **CEO** | Role with `level=ceo` granting all permissions | `{"estates": ["create","view","list","update","delete"], ...}` |
| **C-suite** | Role per c-level, e.g. `level=cfo` | CFO gets finance-heavy permissions |
| **Board** | Role with `level=board_member` | Board resolutions, shareholders, etc. |
| **Manager** | Role with `level=manager` | Branch-scoped: approve leave, manage team, etc. |
| **Head of Dept** | Role with `level=head_hr` etc. | Department-scoped: manage their dept across branches |
| **High / Senior** | Role with `level=high` or `level=senior` | More access than mid-level, less than head |
| **Mid / Junior** | Role with specific level | Standard work permissions |
| **Intern** | Role with `level=intern` or the "All Employees" role | Minimal: view_own, create leave, etc. |
| **Everyone** | Role with `level=None, dept=None, unit=None` | Self-service basics: view_own profile, view announcements, etc. |

**CEO has NO implicit bypass.** They must be assigned permissions through a role, just like everyone else. This is auditable and revocable.

---

## What Still Needs to Be Built

### 1. The `require_permission` decorator

Replaces `owns_or_above` at every endpoint. Logic:

```python
@require_permission("leave_requests", "view", owner_field="employee__user")
def get_leave_request(request, leave_id: int):
    ...
```

The decorator:
1. Gets `employee = request.user.employee_profile`
2. Checks `Role.employee_has_permission(employee, resource, action)`
3. If yes → allow (broad access)
4. If no, but `owner_field` is set → check `action_own` variant
   - If yes → set `request._perm_owner_only = True` (view will filter to owned records)
   - If no → return 403
5. If no `owner_field` → return 403

### 2. Branch/department queryset scoping

After the decorator runs, views filter data based on the employee's level:

```python
def apply_scope(request, queryset, branch_field="branch", department_field="department"):
    employee = request.user.employee_profile
    level = employee.level

    if level.is_branch_scoped:
        # Manager and below: only their branch
        return queryset.filter(**{branch_field: employee.branch})
    elif level.is_head:
        # Head of department: their department across all branches
        return queryset.filter(**{department_field: employee.department})
    else:
        # C-suite / board: everything
        return queryset
```

### 3. Default roles via data migration

Seed roles so the system works immediately:

```
"All Employees"  → level=None  → { view_own profile, view_own docs, view announcements,
                                    create leave, view_own leave, view dashboard }

"Head of HR"     → level=head_hr → { employees: [create, view, list, update, exit],
                                      leave_requests: [view, list, approve, reject],
                                      payroll: [list, process_batch], ... }

"Branch Manager" → level=manager → { employees: [view, list],
                                      leave_requests: [view, list, approve, reject],
                                      estates: [create, view, list, update], ... }

"CEO"            → level=ceo → { ALL resources: ALL actions }
```

### 4. Migrate endpoints (phase by phase)

Replace every `owns_or_above(...)` call with `@require_permission(...)`. The old system stays alongside until fully migrated.

---

## Potential Downsides

1. **Performance** — `employee_has_permission` hits the DB on every request. Cache the employee's merged permission set in Redis/Django cache (~60s TTL).

2. **Initial setup** — Someone must create roles with correct permissions before the system enforces anything. Solve with a data migration.

3. **Debugging** — "Why can't user X do Y?" Add a `GET /roles/employees/{user_id}/permissions` endpoint that returns the full merged permission set.

4. **Head level granularity** — If you add a new department, you need a new `head_*` level choice and migration. This is intentional (explicit > implicit) but means a code change for new departments.

5. **`__contains` on JSONField** — Works on PostgreSQL (`@>` operator). Add a GIN index on `permissions` for performance at scale.
