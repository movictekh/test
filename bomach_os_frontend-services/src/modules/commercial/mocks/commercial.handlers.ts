import { delay, http, HttpResponse } from 'msw'
import { MOCK_API_PREFIX } from '@/mocks/mock-api'

import { env } from '@/shared/config/env'
import { ensureMockOrderFromCommercialSource } from '@/modules/fulfillment/mocks/fulfillment.mock-db'
import { getServiceAdministrationWorkspace } from '@/modules/service-administration/mocks/service-administration.mock-db'

import {
  createMockInvoice,
  recordMockPayment,
  decideMockApproval,
  createMockQuotation,
  createMockServiceRequest,
  getCommercialWorkspace,
  updateMockQuotation,
  updateMockServiceRequest,
} from './commercial.mock-db'
import type {
  CreateInvoiceInput,
  RecordPaymentInput,
  DecideApprovalInput,
  CreateQuotationInput,
  CreateServiceRequestInput,
  ServiceRequestStatus,
  UpdateQuotationInput,
} from '../types/commercial.types'

const endpoint = (path: string) => `${env.apiBaseUrl}${path}`

export const commercialHandlers = [
  http.get(endpoint(`${MOCK_API_PREFIX}/commercial`), async () => {
    await delay(180)
    return HttpResponse.json(getCommercialWorkspace())
  }),

  http.post(endpoint(`${MOCK_API_PREFIX}/commercial/requests`), async ({ request }) => {
    await delay(260)
    const body = (await request.json()) as CreateServiceRequestInput
    if (
      !body.client ||
      !body.phone ||
      !body.service ||
      !body.branch ||
      !body.details ||
      !body.dueAt
    ) {
      return HttpResponse.json({ detail: 'Complete all required request fields.' }, { status: 422 })
    }
    return HttpResponse.json(createMockServiceRequest(body), { status: 201 })
  }),

  http.post(endpoint(`${MOCK_API_PREFIX}/commercial/quotations`), async ({ request }) => {
    await delay(260)
    const body = (await request.json()) as CreateQuotationInput
    if (
      !body.requestId ||
      !body.validUntil ||
      !body.paymentTerms ||
      Number(body.serviceFee) < 0 ||
      Number(body.otherCharges) < 0 ||
      Number(body.discount) < 0
    ) {
      return HttpResponse.json(
        { detail: 'Complete the quotation offer fields before saving.' },
        { status: 422 },
      )
    }
    return HttpResponse.json(createMockQuotation(body), { status: 201 })
  }),

  http.patch(
    endpoint(`${MOCK_API_PREFIX}/commercial/quotations/:quotationId`),
    async ({ params, request }) => {
      await delay(220)
      const body = (await request.json()) as UpdateQuotationInput
      return HttpResponse.json(updateMockQuotation(String(params.quotationId), body))
    },
  ),

  http.post(endpoint(`${MOCK_API_PREFIX}/commercial/invoices`), async ({ request }) => {
    await delay(220)
    const body = (await request.json()) as CreateInvoiceInput

    if (!body.quotationId || !body.dueAt || !body.schedule || Number(body.amount) <= 0) {
      return HttpResponse.json(
        { detail: 'Complete the invoice amount, schedule and due date.' },
        { status: 422 },
      )
    }

    return HttpResponse.json(createMockInvoice(body), {
      status: 201,
    })
  }),

  http.post(
    endpoint(`${MOCK_API_PREFIX}/commercial/invoices/:invoiceId/payments`),
    async ({ params, request }) => {
      await delay(220)
      const body = (await request.json()) as RecordPaymentInput

      const commercialWorkspace = recordMockPayment({
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
        const request = commercialWorkspace.requests.find((item) => item.id === invoice.requestId)

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
            workflowStages: workflow?.stages.map((stage) => stage.name) ??
              service?.workflowStages ?? ['Order Setup', 'Execution', 'Review', 'Handover'],
          })
        }
      }

      return HttpResponse.json(commercialWorkspace)
    },
  ),

  http.patch(
    endpoint(`${MOCK_API_PREFIX}/commercial/approvals/:approvalId`),
    async ({ params, request }) => {
      await delay(180)
      const body = (await request.json()) as DecideApprovalInput

      return HttpResponse.json(
        decideMockApproval({
          ...body,
          approvalId: String(params.approvalId),
        }),
      )
    },
  ),

  http.patch(
    endpoint(`${MOCK_API_PREFIX}/commercial/requests/:requestId`),
    async ({ params, request }) => {
      await delay(180)
      const body = (await request.json()) as {
        status?: ServiceRequestStatus
        owner?: string
        nextAction?: string
        dueAt?: string
        estimate?: number
        activity?: {
          at: string
          title: string
          actor: string
          description: string
        }
      }
      return HttpResponse.json(updateMockServiceRequest(String(params.requestId), body))
    },
  ),
]
