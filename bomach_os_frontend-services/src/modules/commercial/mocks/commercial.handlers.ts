import { delay, http, HttpResponse } from 'msw'

import { env } from '@/shared/config/env'

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
  http.get(endpoint('/ui-prototype/commercial'), async () => {
    await delay(180)
    return HttpResponse.json(getCommercialWorkspace())
  }),

  http.post(endpoint('/ui-prototype/commercial/requests'), async ({ request }) => {
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

  http.post(endpoint('/ui-prototype/commercial/quotations'), async ({ request }) => {
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
    endpoint('/ui-prototype/commercial/quotations/:quotationId'),
    async ({ params, request }) => {
      await delay(220)
      const body = (await request.json()) as UpdateQuotationInput
      return HttpResponse.json(updateMockQuotation(String(params.quotationId), body))
    },
  ),

  http.post(endpoint('/ui-prototype/commercial/invoices'), async ({ request }) => {
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
    endpoint('/ui-prototype/commercial/invoices/:invoiceId/payments'),
    async ({ params, request }) => {
      await delay(220)
      const body = (await request.json()) as RecordPaymentInput

      return HttpResponse.json(
        recordMockPayment({
          ...body,
          invoiceId: String(params.invoiceId),
        }),
      )
    },
  ),

  http.patch(
    endpoint('/ui-prototype/commercial/approvals/:approvalId'),
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
    endpoint('/ui-prototype/commercial/requests/:requestId'),
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
