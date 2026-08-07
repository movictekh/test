#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ! -f package.json ]] || ! grep -q '"name": "bomach_os_frontend-services"' package.json; then
  echo "Error: run this from bomach_os_frontend-services."
  exit 1
fi

python3 <<'PY'
from pathlib import Path

# Types
path = Path('src/modules/fulfillment/types/fulfillment.types.ts')
text = path.read_text()
if 'export interface CommercialOrderHandoffInput' not in text:
    text += "\nexport interface CommercialOrderHandoffInput {\n  requestId: string\n  quotationId: string\n  invoiceId: string\n  client: string\n  service: string\n  division: string\n  value: number\n  dueAt: string\n  owner: string\n  mode: string\n  paymentReady: boolean\n  workflowStages: string[]\n}\n"
path.write_text(text)

# Rules
path = Path('src/modules/fulfillment/workspaces/fulfillment-workflow.rules.ts')
text = path.read_text()
if 'commercialSourceAlreadyOrdered' not in text:
    text += "\nexport function commercialSourceAlreadyOrdered(\n  orders: Array<{ requestId: string; quotationId?: string; invoiceId?: string }>,\n  source: { requestId: string; quotationId: string; invoiceId: string },\n): boolean {\n  return orders.some(\n    (order) =>\n      order.invoiceId === source.invoiceId ||\n      order.quotationId === source.quotationId ||\n      order.requestId === source.requestId,\n  )\n}\n"
path.write_text(text)

# Fulfillment mock DB
path = Path('src/modules/fulfillment/mocks/fulfillment.mock-db.ts')
text = path.read_text()
text = text.replace('  CreateServiceOrderInput,\n', '  CommercialOrderHandoffInput,\n  CreateServiceOrderInput,\n', 1)
text = text.replace("  taskProgressForStatus,\n} from '../workspaces/fulfillment-workflow.rules'", "  taskProgressForStatus,\n  commercialSourceAlreadyOrdered,\n} from '../workspaces/fulfillment-workflow.rules'", 1)
if 'export function ensureMockOrderFromCommercialSource' not in text:
    anchor = 'export function createMockOrder(input: CreateServiceOrderInput): FulfillmentWorkspace {'
    idx = text.find(anchor)
    if idx < 0: raise SystemExit('createMockOrder anchor not found')
    helper = '''export function ensureMockOrderFromCommercialSource(
  input: CommercialOrderHandoffInput,
): FulfillmentWorkspace {
  if (
    commercialSourceAlreadyOrdered(orders, {
      requestId: input.requestId,
      quotationId: input.quotationId,
      invoiceId: input.invoiceId,
    })
  ) {
    return getFulfillmentWorkspace()
  }

  const stamp = Date.now().toString().slice(-8)
  const id = `ORD-${stamp}`
  const workflowStages =
    input.workflowStages.length > 0
      ? input.workflowStages.slice(0, 6)
      : ['Order Setup', 'Execution', 'Review', 'Handover']

  orders.unshift({
    id,
    requestId: input.requestId,
    quotationId: input.quotationId,
    invoiceId: input.invoiceId,
    client: input.client,
    service: input.service,
    division: input.division,
    mode: input.mode,
    status: input.paymentReady ? 'Active' : 'Pending Mobilisation',
    progress: 0,
    owner: input.owner,
    startAt: today(),
    dueAt: input.dueAt,
    value: input.value,
    stage: workflowStages[0] ?? 'Order Setup',
    nextAction: input.paymentReady ? 'Begin fulfillment' : 'Confirm mobilisation',
    paymentReady: input.paymentReady,
    milestones: workflowStages.map((name, index) => ({
      id: `${id}-M${index + 1}`,
      name,
      status: index === 0 ? 'Active' : 'Pending',
    })),
    activities: [
      activity(
        `${id}-A1`,
        nowIso(),
        'Order created',
        'System',
        `Created from ${input.invoiceId} after commercial payment eligibility was confirmed.`,
      ),
    ],
  })

  return getFulfillmentWorkspace()
}

'''
    text = text[:idx] + helper + text[idx:]
path.write_text(text)

# Commercial payment handler
path = Path('src/modules/commercial/mocks/commercial.handlers.ts')
text = path.read_text()
if 'ensureMockOrderFromCommercialSource' not in text:
    text = text.replace("import { env } from '@/shared/config/env'\n", "import { env } from '@/shared/config/env'\nimport { ensureMockOrderFromCommercialSource } from '@/modules/fulfillment/mocks/fulfillment.mock-db'\nimport { getServiceAdministrationWorkspace } from '@/modules/service-administration/mocks/service-administration.mock-db'\n", 1)
old = "    return HttpResponse.json(\n        recordMockPayment({\n          ...body,\n          invoiceId: String(params.invoiceId),\n        }),\n      )\n"
new = '''    const commercialWorkspace = recordMockPayment({
      ...body,
      invoiceId: String(params.invoiceId),
    })

    const invoice = commercialWorkspace.invoices.find(
      (item) => item.id === String(params.invoiceId),
    )

    if (invoice && invoice.amountPaid > 0) {
      const quotation = commercialWorkspace.quotations.find(
        (item) => item.id === invoice.quotationId,
      )
      const request = commercialWorkspace.requests.find(
        (item) => item.id === invoice.requestId,
      )

      if (quotation && request && quotation.status === 'Accepted') {
        const serviceAdministration = getServiceAdministrationWorkspace()
        const service = serviceAdministration.services.find(
          (item) => item.name === invoice.service,
        )
        const workflow = serviceAdministration.workflows.find(
          (item) => item.serviceName === invoice.service && item.status === 'active',
        )

        ensureMockOrderFromCommercialSource({
          requestId: request.id,
          quotationId: quotation.id,
          invoiceId: invoice.id,
          client: invoice.client,
          service: invoice.service,
          division: request.division || service?.division || 'Service Operations',
          value: invoice.total,
          dueAt: request.dueAt || invoice.dueAt,
          owner: service?.owner || 'Service Manager',
          mode: service?.fulfilmentMode || 'Managed service case',
          paymentReady: true,
          workflowStages:
            workflow?.stages.map((stage) => stage.name) ??
            service?.workflowStages ??
            ['Order Setup', 'Execution', 'Review', 'Handover'],
        })
      }
    }

    return HttpResponse.json(commercialWorkspace)
'''
if old not in text: raise SystemExit('record payment handler anchor not found')
text = text.replace(old, new, 1)
path.write_text(text)

# Commercial page invalidates fulfillment cache after payment
path = Path('src/modules/commercial/pages/CommercialSectionPage.tsx')
text = path.read_text()
if 'fulfillmentKeys' not in text:
    text = text.replace("import { serviceAdministrationQueries } from '@/modules/service-administration/api/service-administration.queries'\n", "import { serviceAdministrationQueries } from '@/modules/service-administration/api/service-administration.queries'\nimport { fulfillmentKeys } from '@/modules/fulfillment/api/fulfillment.keys'\n", 1)
old = "    onSuccess: (workspace) => {\n      queryClient.setQueryData(commercialKeys.workspace(), workspace)\n      toast.success('Payment recorded')\n    },\n"
new = "    onSuccess: (workspace) => {\n      queryClient.setQueryData(commercialKeys.workspace(), workspace)\n      void queryClient.invalidateQueries({ queryKey: fulfillmentKeys.workspace() })\n      toast.success('Payment recorded')\n    },\n"
if old not in text: raise SystemExit('recordPayment onSuccess anchor not found')
text = text.replace(old, new, 1)
path.write_text(text)

# Fulfillment page: manual create is truly manual; remove Commercial free-text matching
path = Path('src/modules/fulfillment/pages/FulfillmentSectionPage.tsx')
text = path.read_text()
text = text.replace("import { commercialQueries } from '@/modules/commercial/api/commercial.queries'\n", '')
text = text.replace('  const commercialQuery = useQuery(commercialQueries.workspace())\n', '')
text = text.replace('  if (query.isPending || commercialQuery.isPending || serviceQuery.isPending) {', '  if (query.isPending || serviceQuery.isPending) {')
text = text.replace('  if (query.isError || commercialQuery.isError || serviceQuery.isError) {\n    const sourceError = query.error ?? commercialQuery.error ?? serviceQuery.error', '  if (query.isError || serviceQuery.isError) {\n    const sourceError = query.error ?? serviceQuery.error')
text = text.replace('          void commercialQuery.refetch()\n', '')
start = text.find("          onSubmit={(draft) => {\n            const selectedService = services.find((service) => service.name === draft.service)")
if start < 0: raise SystemExit('manual create block start not found')
end_marker = "          }}\n        />\n"
end = text.find(end_marker, start)
if end < 0: raise SystemExit('manual create block end not found')
replacement = '''          onSubmit={(draft) => {
            const selectedService = services.find(
              (service) => service.name === draft.service,
            )

            createOrder.mutate({
              ...draft,
              division: selectedService?.division ?? 'Service Operations',
              paymentReady: false,
              workflowStages: selectedService?.workflowStages.length
                ? selectedService.workflowStages
                : ['Order Setup', 'Execution', 'Review', 'Handover'],
            })
          }}
        />
'''
text = text[:start] + replacement + text[end + len(end_marker):]
path.write_text(text)

# Tests
path = Path('src/modules/fulfillment/workspaces/fulfillment-workflow.rules.test.ts')
text = path.read_text()
text = text.replace("  taskProgressForStatus,\n} from './fulfillment-workflow.rules'", "  taskProgressForStatus,\n  commercialSourceAlreadyOrdered,\n} from './fulfillment-workflow.rules'", 1)
if 'detects an existing commercial source order' not in text:
    text = text.replace('\n})\n', '''
  it('detects an existing commercial source order by exact linked IDs', () => {
    const orders = [{ requestId: 'REQ-1', quotationId: 'Q-1', invoiceId: 'INV-1' }]
    expect(
      commercialSourceAlreadyOrdered(orders, {
        requestId: 'REQ-1',
        quotationId: 'Q-1',
        invoiceId: 'INV-1',
      }),
    ).toBe(true)
    expect(
      commercialSourceAlreadyOrdered(orders, {
        requestId: 'REQ-2',
        quotationId: 'Q-2',
        invoiceId: 'INV-2',
      }),
    ).toBe(false)
  })

  it('prevents duplicate fulfillment when a canonical source ID is reused', () => {
    const orders = [{ requestId: 'REQ-10', quotationId: 'Q-10', invoiceId: 'INV-10' }]
    expect(
      commercialSourceAlreadyOrdered(orders, {
        requestId: 'REQ-99',
        quotationId: 'Q-99',
        invoiceId: 'INV-10',
      }),
    ).toBe(true)
    expect(
      commercialSourceAlreadyOrdered(orders, {
        requestId: 'REQ-99',
        quotationId: 'Q-10',
        invoiceId: 'INV-99',
      }),
    ).toBe(true)
  })
})
''', 1)
path.write_text(text)

# Docs
path = Path('docs/ui-rebuild/updates/UI_3_01_02_Fulfillment_Orders_and_Tasks.md')
text = path.read_text()
if '## Final commercial handoff correction' not in text:
    text += "\n## Final commercial handoff correction\n\nThe Stage 2 → Stage 3 handoff no longer depends on typed client/service matching. Payment confirmation carries the exact invoice ID into fulfillment, resolves the linked quotation and request, creates one Service Order, and invalidates the fulfillment Query. The order stores requestId, quotationId, and invoiceId, and duplicate creation is prevented by those canonical IDs. Manual Create Order remains the literal HTML manual workflow and does not pretend to be a Commercial conversion.\n"
path.write_text(text)
PY

npm run format
npm run check
npm run test -- --run
npm run build:storybook

echo
echo "UI-3.01 exact commercial handoff fix applied."
