# Role-Based Permissions: Analysis & Recommendations



### The `owns_or_above` System (Current)

Every protected endpoint calls `owns_or_above()` with three inputs:

1. **`owns`** — does the requesting user own the resource?
2. **`employee_level`** — the user's level (intern → CEO)
3. **`least_required_level`** — the minimum level needed for the action

The logic is: if you own the resource you're in; otherwise your level must meet the minimum.

**`incharge_of_section`** is always hardcoded to `True` across the entire backend — meaning the "section authority" dimension was planned but never implemented. Every permission check today is purely level-based.

### Coverage Gaps

| Module | Endpoints | Have checks | Missing checks |
|--------|-----------|-------------|----------------|
| User API | ~60 | ~45 | ~15 (dashboard, stats, cart, biometric) |
| HR API | ~50 | ~25 | ~25 (awards, disciplinary, evaluations, KPIs, scorecards, training, work reports, performance reviews) |
| Services API | ~40 | ~3 (expenses only) | ~37 (budgets, invoices, leads, orders, payments, quotes, services, marketing, documents, content) |
| Operations API | ~30 | 0 | ~30 (projects, tasks, contracts, worksites, timelines, milestones, equipment) |

**~100 out of ~180 endpoints have no permission checks at all.** The services and operations modules are effectively open to any authenticated user.

### Other Issues

- **HR API uses raw strings** (`'manager'`) while user API uses the enum (`EmployeeLevel.LevelChoices.MANAGER`). Both happen to work because `check_strength` does a dict lookup on the string value, but it's inconsistent and fragile.
- **Duplicate code**: `owns_or_above` and `check_strength` are copy-pasted between `user/utils/perm.py` and `hr/utils/perm.py`.
- **No resource-level granularity**: A MANAGER can do everything a MANAGER can do. You can't say "this manager can manage employees but not invoices."

---

## What the New Role System Gives You

The `PERMISSIONS_MAP` + JSONField approach you've built is solid. Here's what's good about it:

### Strengths

1. **Granular resource-action pairs** — `{"employees": ["create", "view"], "invoices": ["list"]}` lets you give one manager invoice access without employee access. The old system can't do this at all.

2. **Single source of truth** — `PERMISSIONS_MAP` defines every valid resource and action in one place. The frontend reads it via `/permissions-map` to render a checkbox grid. Adding a new resource/action means updating one dict.

3. **Validation built in** — `_validate_permissions()` rejects unknown resources or actions at save time. You can't create a role with `{"fake_resource": ["delete"]}`.

4. **Scoping via level + unit** — A role can optionally be restricted to employees at a specific level or in a specific unit. This replaces the `incharge_of_section` concept that was never implemented.

5. **Multiple roles per employee** — The M2M relationship means an employee can hold several roles. Permissions are the union of all their roles. This is standard RBAC and is the right approach.

6. **`employee_has_permission` static method** — Clean one-line check: `Role.employee_has_permission(employee, "invoices", "create")`. Uses Django's `__contains` JSON lookup so it hits the database efficiently.

### Things to Watch Out For

#### 1. You Still Need Level-Based Access as a Fallback

The `owns_or_above` pattern handles one thing roles don't: **ownership**. An intern should be able to view their own leave requests even without a "leave_requests: view" permission. If you remove `owns_or_above` entirely, you'll need to handle the "owns" case separately.

**Recommendation**: Keep an ownership check as a separate concept. The new check should be:

```
Can user do X?
  → YES if they own the resource (for read/update operations on personal data)
  → YES if any of their roles grant the permission
  → NO otherwise
```

Don't bake ownership into the role system — it's a separate concern.

#### 2. CEO / Super-Admin Bypass

Right now a CEO can do everything because their level is always >= any required level. With roles, a CEO without any roles assigned would be locked out of everything. You need to decide:

- **Option A**: CEO-level employees automatically bypass all role checks (simplest, matches current behavior)
- **Option B**: Create a "Super Admin" role with all permissions and assign it to CEOs
- **Option C**: No bypass — CEOs get roles like everyone else

Option A is pragmatic for a company like yours where the CEO should genuinely have full access. Option B is more "correct" from an RBAC perspective. I'd suggest **Option A with Option B available** — CEO bypasses by default, but you can also create explicit super-admin roles for non-CEO users who need full access.

#### 3. The `incharge_of_section` Dimension

This was hardcoded `True` everywhere, meaning it was never actually enforced. The role system's `unit` scoping partially replaces this — you can create a role scoped to a specific unit. But consider whether you actually need section/unit-scoped permissions at all, or if resource-action granularity is sufficient. Don't build complexity you won't use.

#### 4. Migration Path for ~100 Unprotected Endpoints

The biggest win here isn't replacing existing `owns_or_above` calls — it's protecting the ~100 endpoints that have **zero checks**. When you wire up the role system, do it for ALL endpoints, not just the ones that already have `owns_or_above`. This is the real security payoff.

#### 5. Performance Consideration

`Role.employee_has_permission()` hits the database on every call. For endpoints that check multiple permissions or are called frequently, consider:

- Prefetching the user's roles and permissions at authentication time (middleware or JWT payload)
- Caching the merged permission set on the request object
- This isn't urgent — the DB query is a simple indexed lookup — but keep it in mind at scale

#### 6. The `permissions_apply_to` Method May Be Unnecessary Complexity

The `permissions_apply_to` check verifies that the role's level/unit scoping matches the employee. But if you're assigning roles to employees via the M2M relationship, the assignment itself should be the gate. You'd check scoping at **assignment time** (prevent assigning an "Intern HR" role to a Manager), not at **permission-check time**.

Checking scoping at both assignment and runtime adds complexity. Pick one:
- **Check at assignment time only** (simpler, recommended) — trust that the M2M assignment is correct
- **Check at runtime** — more defensive but slower and more complex

---

## Recommended New Permission Check Flow

Replace `owns_or_above` with a utility like this:

```python
def require_permission(request, resource: str, action: str, obj=None):
    """
    Central permission gate for all endpoints.

    - CEO+ bypasses all checks
    - Owner of the resource gets access (for personal data)
    - Otherwise checks assigned roles
    """
    employee = request.user.employee_profile
    level = employee.level.level if employee.level else None

    # 1. CEO/C-suite bypass
    if level and check_strength(level, 'ceo'):
        return

    # 2. Ownership check (optional, for personal data)
    if obj is not None and hasattr(obj, 'user_id') and obj.user_id == request.user.id:
        return
    if obj is not None and hasattr(obj, 'employee') and obj.employee_id == employee.id:
        return

    # 3. Role-based check
    if Role.employee_has_permission(employee, resource, action):
        return

    raise PermissionError("You do not have permission to perform this action.")
```

Then endpoint code becomes:

```python
def create_invoice(request, payload: InvoiceCreateSchema):
    require_permission(request, "estate_invoices", "create")
    ...
```

This is cleaner than the current 5-line `owns_or_above` block in every endpoint.

---

## Rollout Strategy

### Phase 1: Wire Up the New Check (Without Removing the Old One)

Add `require_permission()` calls to the ~100 **unprotected** endpoints first. This immediately closes the biggest security gap without touching working code.

### Phase 2: Replace `owns_or_above` in Existing Endpoints

Swap out `owns_or_above` for `require_permission` in the ~80 endpoints that already have checks. Do this module by module (user → hr → services → operations) so you can test in chunks.

### Phase 3: Remove Old Code

Delete `owns_or_above`, `check_strength` from both `user/utils/perm.py` and `hr/utils/perm.py` once all endpoints are migrated. Remove the duplicate HR copy.

### Phase 4: Create Default Roles

Create seed data / management command that creates sensible default roles:
- **Super Admin** — all permissions (for CEO and designated admins)
- **Department Head** — manage employees, reviews, documents in their unit
- **HR Manager** — leave requests, payroll, job postings, applicants
- **Finance** — invoices, payments, expenses, budgets
- **Operations Manager** — projects, tasks, contracts, worksites
- **Viewer** — read-only access across modules

---

## Summary

| Aspect | Old System | New Role System |
|--------|-----------|-----------------|
| Granularity | Level-based only (MANAGER can do everything a MANAGER can do) | Resource + action pairs |
| Coverage | ~80 endpoints protected, ~100 open | Can protect all ~180 endpoints |
| Flexibility | None — hardcoded level per endpoint | Configurable per-employee via admin/API |
| Ownership | Built into `owns_or_above` | Needs separate handling (simple) |
| Frontend support | None | `/permissions-map` endpoint for checkbox grid |
| Code duplication | `owns_or_above` copy-pasted in 2 apps | Single `require_permission` utility |

**Bottom line**: The role model design is good. The JSONField + PERMISSIONS_MAP approach is the right pattern for your scale. The main risks are: (1) forgetting to handle ownership/personal-data access, (2) locking out CEO-level users if they have no roles assigned, and (3) trying to do the migration all at once instead of phased. Address those three things and the transition will be smooth.
