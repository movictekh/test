import { describe, expect, it } from 'vitest'

import { operationsNavigation } from '@/app/navigation'
import { getCommercialWorkspace } from '@/modules/commercial/mocks/commercial.mock-db'
import { getExperienceIntelligenceWorkspace } from '@/modules/experience-intelligence/mocks/experience-intelligence.mock-db'
import {
  deriveFeedbackSummary,
  deriveReportSnapshot,
} from '@/modules/experience-intelligence/workspaces/experience-intelligence.rules'
import { getFulfillmentWorkspace } from '@/modules/fulfillment/mocks/fulfillment.mock-db'
import { getServiceAdministrationWorkspace } from '@/modules/service-administration/mocks/service-administration.mock-db'
import { getSpecializedWorkspace } from '@/modules/specialized-services/mocks/specialized-services.mock-db'
import { getRecordDestination } from '@/shared/navigation'

function navigationLabels(): string[] {
  return operationsNavigation.flatMap((group) => group.items.map((item) => item.label))
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

    for (const task of fulfillment.tasks.filter((item) => item.orderId.startsWith('ORD-'))) {
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
    const report = deriveReportSnapshot(commercial, fulfillment, experience.feedback)

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
