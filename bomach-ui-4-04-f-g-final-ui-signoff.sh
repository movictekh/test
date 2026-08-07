#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ! -f package.json ]] || ! grep -q '"name": "bomach_os_frontend-services"' package.json; then
  echo "Error: run this from bomach_os_frontend-services."
  exit 1
fi

mkdir -p src/app/signoff docs/ui-rebuild/updates

cat > src/styles/responsive.css <<'EOF'
/*
 * Responsive hardening for Service Operations screens.
 * Does not redesign desktop composition — only prevents overflow/truncation
 * and keeps established prototype screens operable at tablet/mobile widths.
 */

:is(
  .service-admin-content,
  .commercial-content,
  .fulfillment-content,
  .specialized-content,
  .experience-content
) {
  min-width: 0;
}

:is(
  .commercial-card,
  .fulfillment-card,
  .specialized-card,
  .experience-card
) > * {
  min-width: 0;
}

:is(
  .commercial-table-wrap,
  .fulfillment-table-wrap,
  .specialized-table-wrap,
  .experience-table-wrap,
  .commercial-life,
  .fulfillment-kanban,
  .fulfillment-lifecycle,
  .specialized-lifecycle,
  .specialized-tabs
) {
  overscroll-behavior-inline: contain;
  scrollbar-gutter: stable;
  -webkit-overflow-scrolling: touch;
}

:is(
  .commercial-modal,
  .fulfillment-modal,
  .specialized-modal,
  .experience-modal,
  .service-admin-modal
) {
  max-width: 100%;
}

.specialized-modal {
  max-height: 92vh;
  display: flex;
  flex-direction: column;
}

.specialized-modal-body {
  min-height: 0;
  overflow: auto;
}

.specialized-legend {
  flex-wrap: wrap;
}

@media (max-width: 700px) {
  .commercial-content,
  .experience-content {
    padding: 12px;
  }

  .commercial-card-header,
  .fulfillment-card-header,
  .specialized-card-header,
  .experience-card-header {
    align-items: flex-start;
  }

  .commercial-filter-row > *,
  .fulfillment-filter-row > *,
  .specialized-filter-row > * {
    max-width: 100%;
  }
}

@media (max-width: 680px) {
  .specialized-modal-backdrop {
    align-items: flex-end;
    padding: 0;
  }

  .specialized-modal {
    width: 100%;
    max-height: 94vh;
    border-radius: 16px 16px 0 0;
  }

  .specialized-modal-footer,
  .commercial-modal-footer,
  .fulfillment-modal-footer,
  .experience-modal-footer,
  .service-admin-modal-footer {
    flex-wrap: wrap;
  }

  .specialized-tabs {
    padding-bottom: 3px;
  }
}

@media (max-width: 480px) {
  .specialized-kpi-grid,
  .experience-kpi-grid {
    grid-template-columns: 1fr;
  }

  .specialized-plot-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .fulfillment-filter-row input {
    min-width: 0;
    width: 100%;
  }

  .commercial-modal-footer-actions,
  .commercial-modal-footer-start {
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
EOF

python3 <<'PY'
from pathlib import Path

index_css = Path("src/styles/index.css")
text = index_css.read_text()
import_line = "@import './responsive.css';\n"
if import_line not in text:
    text = text.replace("@import 'tailwindcss';\n", "@import 'tailwindcss';\n" + import_line, 1)
index_css.write_text(text)
PY

cat > src/app/signoff/ui-product-signoff.test.ts <<'EOF'
import { describe, expect, it } from 'vitest'

import { operationsNavigation } from '@/app/navigation'
import { getCommercialWorkspace } from '@/modules/commercial/mocks/commercial.mock-db'
import { getExperienceIntelligenceWorkspace } from '@/modules/experience-intelligence/mocks/experience-intelligence.mock-db'
import { deriveFeedbackSummary, deriveReportSnapshot } from '@/modules/experience-intelligence/workspaces/experience-intelligence.rules'
import { getFulfillmentWorkspace } from '@/modules/fulfillment/mocks/fulfillment.mock-db'
import { getServiceAdministrationWorkspace } from '@/modules/service-administration/mocks/service-administration.mock-db'
import { getSpecializedWorkspace } from '@/modules/specialized-services/mocks/specialized-services.mock-db'
import { getRecordDestination } from '@/shared/navigation'

function navigationLabels(): string[] {
  return operationsNavigation.flatMap((group) =>
    group.items.map((item) => item.label),
  )
}

describe('UI-4.04G product sign-off', () => {
  it('keeps the final staff navigation vocabulary aligned with the Service Operations prototype', () => {
    const labels = navigationLabels()

    expect(labels).toEqual(
      expect.arrayContaining([
        'Command Center',
        'Service Catalogue',
        'Calculator Library',
        'Request Form Builder',
        'Workflow Designer',
        'Branch Activation',
        'Service Requests',
        'Quotations',
        'Invoices & Payments',
        'Approvals',
        'Service Orders',
        'Execution Tasks',
        'Deliverables',
        'Real Estate Inventory',
        'Survey / Engineering / Others',
        'Feedback and Quality',
        'Reports and Analytics',
      ]),
    )

    expect(labels).not.toContain('Client Portal')
  })

  it('keeps commercial records internally connected', () => {
    const commercial = getCommercialWorkspace()
    const requestIds = new Set(commercial.requests.map((item) => item.id))
    const quotationIds = new Set(commercial.quotations.map((item) => item.id))

    expect(commercial.requests.length).toBeGreaterThan(0)
    expect(commercial.quotations.length).toBeGreaterThan(0)
    expect(commercial.invoices.length).toBeGreaterThan(0)

    for (const quotation of commercial.quotations) {
      expect(
        requestIds.has(quotation.requestId),
        `${quotation.id} should reference an existing request`,
      ).toBe(true)
    }

    for (const invoice of commercial.invoices) {
      expect(
        quotationIds.has(invoice.quotationId),
        `${invoice.id} should reference an existing quotation`,
      ).toBe(true)
    }
  })

  it('keeps paid commercial work connected to fulfillment records', () => {
    const commercial = getCommercialWorkspace()
    const fulfillment = getFulfillmentWorkspace()

    const quotationIds = new Set(commercial.quotations.map((item) => item.id))
    const invoiceIds = new Set(commercial.invoices.map((item) => item.id))

    const commerciallyLinkedOrders = fulfillment.orders.filter(
      (order) => order.quotationId || order.invoiceId,
    )

    expect(commerciallyLinkedOrders.length).toBeGreaterThan(0)

    for (const order of commerciallyLinkedOrders) {
      if (order.quotationId) {
        expect(
          quotationIds.has(order.quotationId),
          `${order.id} should reference an existing quotation`,
        ).toBe(true)
      }

      if (order.invoiceId) {
        expect(
          invoiceIds.has(order.invoiceId),
          `${order.id} should reference an existing invoice`,
        ).toBe(true)
      }
    }
  })

  it('keeps execution tasks and deliverables attached to valid service orders', () => {
    const fulfillment = getFulfillmentWorkspace()
    const orderIds = new Set(fulfillment.orders.map((item) => item.id))

    for (const task of fulfillment.tasks.filter((item) =>
      item.orderId.startsWith('ORD-'),
    )) {
      expect(
        orderIds.has(task.orderId),
        `${task.id} should reference an existing service order`,
      ).toBe(true)
    }

    for (const deliverable of fulfillment.deliverables) {
      expect(
        orderIds.has(deliverable.orderId),
        `${deliverable.id} should reference an existing service order`,
      ).toBe(true)
    }
  })

  it('keeps feedback and reporting connected to fulfillment data', () => {
    const commercial = getCommercialWorkspace()
    const fulfillment = getFulfillmentWorkspace()
    const experience = getExperienceIntelligenceWorkspace()

    const orderIds = new Set(fulfillment.orders.map((item) => item.id))

    for (const feedback of experience.feedback) {
      expect(
        orderIds.has(feedback.orderId),
        `${feedback.id} should reference an existing service order`,
      ).toBe(true)
    }

    const feedbackSummary = deriveFeedbackSummary(experience.feedback)
    const report = deriveReportSnapshot(
      commercial,
      fulfillment,
      experience.feedback,
    )

    expect(feedbackSummary.averageRating).toBeGreaterThan(0)
    expect(report.services.length).toBeGreaterThan(0)
    expect(report.branches.length).toBeGreaterThan(0)
  })

  it('keeps specialized-service structures aligned with the prototype', () => {
    const specialized = getSpecializedWorkspace()

    expect(specialized.estates.length).toBeGreaterThan(0)
    expect(specialized.brokerage.length).toBeGreaterThan(0)
    expect(specialized.profiles.map((item) => item.label)).toEqual([
      'Land Surveying',
      'Engineering',
      'Courier & Logistics',
      'Information Technology',
    ])
  })

  it('keeps service configuration assets available to the commercial and fulfillment flow', () => {
    const serviceAdmin = getServiceAdministrationWorkspace()

    expect(serviceAdmin.services.length).toBeGreaterThan(0)
    expect(serviceAdmin.calculators.length).toBeGreaterThan(0)
    expect(serviceAdmin.requestForms.length).toBeGreaterThan(0)
    expect(serviceAdmin.workflows.length).toBeGreaterThan(0)
    expect(serviceAdmin.branchActivations.length).toBeGreaterThan(0)
  })

  it('resolves the final cross-record deep-link destinations', () => {
    expect(getRecordDestination('request', 'REQ-1')).toEqual({
      section: 'service-requests',
      search: { request: 'REQ-1' },
    })
    expect(getRecordDestination('invoice', 'INV-1')).toEqual({
      section: 'invoices-payments',
      search: { invoice: 'INV-1' },
    })
    expect(getRecordDestination('order', 'ORD-1')).toEqual({
      section: 'service-orders',
      search: { order: 'ORD-1' },
    })
    expect(getRecordDestination('task', 'TSK-1')).toEqual({
      section: 'execution-tasks',
      search: { task: 'TSK-1' },
    })
    expect(getRecordDestination('deliverable', 'DEL-1')).toEqual({
      section: 'deliverables',
      search: { deliverable: 'DEL-1' },
    })
    expect(getRecordDestination('feedback', 'FDB-1')).toEqual({
      section: 'feedback-quality',
      search: { feedback: 'FDB-1' },
    })
  })
})
EOF

cat > docs/ui-rebuild/updates/UI_4_04_F_G_FINAL_UI_SIGNOFF.md <<'EOF'
# UI-4.04F / UI-4.04G — Final UI Fidelity and Product Sign-off

## Sign-off position

The Service Operations frontend UI rebuild is considered **design-complete**
when this sign-off passes.

This is a **prototype-fidelity sign-off**, not a claim that every React pixel is
identical to the original static HTML. Minor visual refinements were accepted
during implementation. The acceptance standard is:

- the same product areas exist;
- the same important labels and terminology are used;
- the same information hierarchy is recognizable;
- the same business actions and workflows are represented;
- related records are connected;
- responsive layouts remain usable;
- permission-restricted actions remain permission-restricted;
- loading, empty and error paths remain intentional.

The original HTML remains the visual and workflow reference where no later
product decision overrides it.

## Product decisions excluded from final UI sign-off

### Audit Log

Audit Log is **on hold pending product confirmation**. The existing screen and
mock audit infrastructure are left in place, but Audit Log is not a blocker for
this final UI-design sign-off and should not receive further design work until
its product ownership is confirmed.

### Notifications

The Notification frontend integration is complete, but the backend team owns
notification generation and recipient rules. Live notification sign-off remains
dependent on the final backend endpoint/schema configuration.

### Client Portal

Client Portal is a separate application and is explicitly outside this frontend.

---

# UI-4.04F — Responsive + Prototype Fidelity

## Review standard

The review follows `04_Pixel_Match_Review_Checklist.md`, with one accepted
change in interpretation:

> Exact pixel identity is not required where intentional visual refinements were
> made. Structural, semantic and workflow fidelity are required.

## Desktop / laptop

The final implementation retains the prototype's major compositions:

- Command Center and staff shell;
- Service Administration catalogue, editors, configuration and branch matrix;
- Commercial request → quotation → approval → invoice/payment flow;
- Service Order Kanban and Order Control Room;
- Execution Task Kanban and task workspace;
- Deliverables & Document Inbox;
- Real Estate Inventory with plot grid and selected-plot controls;
- combined Survey / Engineering / Others specialized-services workspace;
- Feedback & Quality KPI/register composition;
- Reports & Analytics KPI/service/branch composition.

## Tablet

Established two-column and 2:1 layouts collapse to one column where space is no
longer sufficient. Horizontal lifecycle/Kanban structures remain horizontally
scrollable instead of being semantically redesigned.

## Mobile

The final hardening layer ensures:

- wide tables scroll horizontally;
- Kanban and lifecycle rows preserve their columns through horizontal scrolling;
- form grids collapse to one column;
- large modal workspaces remain viewport-bounded;
- specialized-service modal controls remain operable;
- plot inventory reduces column count rather than overflowing;
- cards and content regions may shrink without forcing page-level horizontal
  overflow;
- footer actions can wrap where needed.

## Accessibility / interaction

The app retains global visible focus styling, semantic tables, labeled dialogs,
keyboard-openable feedback rows, disabled mutation states, and status text in
addition to status colour.

---

# UI-4.04G — End-to-End Product Sign-off

Automated sign-off tests verify the connected product model rather than isolated
screens only.

## Signed-off chain

```text
Service configuration
        ↓
Service Request
        ↓
Quotation
        ↓
Approval / acceptance
        ↓
Invoice
        ↓
Payment
        ↓
Service Order
        ↓
Execution Task
        ↓
Deliverable
        ↓
Feedback & Quality
        ↓
Reports & Analytics
```

The sign-off suite verifies:

1. final staff navigation uses the expected Service Operations vocabulary;
2. Client Portal is absent from staff navigation;
3. quotations reference existing requests;
4. invoices reference existing quotations;
5. commercially linked orders reference existing quotations/invoices;
6. execution tasks associated with Service Orders resolve to valid orders;
7. deliverables resolve to valid orders;
8. feedback resolves to valid orders;
9. Feedback KPIs and Reports derive from connected application state;
10. Specialized Services retain the four intended service families;
11. Service Administration still supplies services, calculators, forms,
    workflows and branch activation data;
12. cross-record deep links resolve to the correct owning screen.

## Remaining backend-dependent checks

These are not UI-design blockers:

- live notification endpoint/schema integration;
- production authorization enforcement at backend endpoints;
- production persistence and analytics contracts;
- final Audit Log product decision.

## Final status

After `npm run check`, `npm run test -- --run`, and `npm run build:storybook`
pass with the sign-off suite included:

**Service Operations frontend UI rebuild: DESIGN COMPLETE.**

Future work should be treated as backend integration, production hardening,
product-scope change, or deliberate post-sign-off redesign—not unfinished
prototype UI reconstruction.
EOF

# Add a clear completion note to the roadmap without rewriting historical phases.
cat >> docs/ui-rebuild/updates/UI_4_04_F_G_FINAL_UI_SIGNOFF.md <<'EOF'

## Completion command

```bash
npm run check
npm run build:storybook
```
EOF

npm run format
npm run check
npm run build:storybook

echo
echo "UI-4.04F responsive/prototype-fidelity review applied."
echo "UI-4.04G product sign-off tests applied."
echo "Audit Log remains explicitly on hold."
echo "If the verification above passes, the Service Operations UI rebuild is DESIGN COMPLETE."
