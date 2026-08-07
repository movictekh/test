import { delay, http, HttpResponse } from 'msw'
import { MOCK_API_PREFIX } from '@/mocks/mock-api'

import { env } from '@/shared/config/env'

import {
  configureMockService,
  createMockService,
  createMockServiceWizard,
  duplicateMockService,
  getServiceAdministrationWorkspace,
  saveMockBranchActivationMatrix,
  saveMockCalculator,
  saveMockRequestForm,
  saveMockWorkflow,
  updateMockBranchActivation,
  updateMockConfigurationStatus,
} from './service-administration.mock-db'

const endpoint = (path: string) => `${env.apiBaseUrl}${path}`
const basePath = `${MOCK_API_PREFIX}/service-administration`

export const serviceAdministrationHandlers = [
  http.get(endpoint(basePath), async () => {
    await delay(180)
    return HttpResponse.json(getServiceAdministrationWorkspace())
  }),

  http.post(endpoint(`${basePath}/services`), async ({ request }) => {
    await delay(260)
    const body = (await request.json()) as {
      name?: string
      code?: string
      division?: string
      description?: string
      owner?: string
    }

    if (!body.name || !body.code || !body.division || !body.owner) {
      return HttpResponse.json(
        {
          code: 'VALIDATION_ERROR',
          detail: 'Complete the required service fields.',
          errors: {
            name: body.name ? undefined : 'Service name is required.',
            code: body.code ? undefined : 'Service code is required.',
            division: body.division ? undefined : 'Division is required.',
            owner: body.owner ? undefined : 'Service owner is required.',
          },
        },
        { status: 422 },
      )
    }

    return HttpResponse.json(
      createMockService({
        name: body.name,
        code: body.code,
        division: body.division,
        description: body.description ?? '',
        owner: body.owner,
      }),
      { status: 201 },
    )
  }),

  http.post(endpoint(`${basePath}/services/wizard`), async ({ request }) => {
    await delay(320)
    const body = await request.json()

    const input = body as Parameters<typeof createMockServiceWizard>[0]
    if (!input.name || !input.code || !input.division || !input.owner) {
      return HttpResponse.json(
        { detail: 'Service name, code, division and owner are required.' },
        { status: 422 },
      )
    }

    return HttpResponse.json(createMockServiceWizard(input), { status: 201 })
  }),

  http.put(endpoint(`${basePath}/services/:serviceId`), async ({ request }) => {
    await delay(260)
    const body = await request.json()
    const workspace = configureMockService(body as Parameters<typeof configureMockService>[0])

    if (!workspace) {
      return HttpResponse.json({ detail: 'Service was not found.' }, { status: 404 })
    }

    return HttpResponse.json(workspace)
  }),

  http.post(endpoint(`${basePath}/services/:serviceId/duplicate`), async ({ params }) => {
    await delay(220)
    const duplicated = duplicateMockService(String(params.serviceId))

    if (!duplicated) {
      return HttpResponse.json({ detail: 'Service was not found.' }, { status: 404 })
    }

    return HttpResponse.json(duplicated, { status: 201 })
  }),

  http.put(endpoint(`${basePath}/calculators/:calculatorId`), async ({ request }) => {
    await delay(240)
    const body = await request.json()
    saveMockCalculator(body as Parameters<typeof saveMockCalculator>[0])
    return HttpResponse.json(getServiceAdministrationWorkspace())
  }),

  http.put(endpoint(`${basePath}/request-forms/:formId`), async ({ request }) => {
    await delay(240)
    const body = await request.json()
    saveMockRequestForm(body as Parameters<typeof saveMockRequestForm>[0])
    return HttpResponse.json(getServiceAdministrationWorkspace())
  }),

  http.put(endpoint(`${basePath}/workflows/:workflowId`), async ({ request }) => {
    await delay(240)
    const body = await request.json()
    saveMockWorkflow(body as Parameters<typeof saveMockWorkflow>[0])
    return HttpResponse.json(getServiceAdministrationWorkspace())
  }),

  http.patch(endpoint(`${basePath}/configuration-status`), async ({ request }) => {
    await delay(180)
    const body = (await request.json()) as {
      entity: 'service' | 'calculator' | 'request-form' | 'workflow'
      id: string
      status: 'active' | 'draft' | 'inactive'
    }
    updateMockConfigurationStatus(body.entity, body.id, body.status)
    return HttpResponse.json(getServiceAdministrationWorkspace())
  }),

  http.put(endpoint(`${basePath}/branch-activation-matrix`), async ({ request }) => {
    await delay(260)
    const body = await request.json()
    const workspace = saveMockBranchActivationMatrix(
      body as Parameters<typeof saveMockBranchActivationMatrix>[0],
    )
    return HttpResponse.json(workspace)
  }),

  http.patch(endpoint(`${basePath}/branch-activation`), async ({ request }) => {
    await delay(180)
    const body = (await request.json()) as {
      id: string
      state: 'active' | 'inactive' | 'setup-required'
    }
    updateMockBranchActivation(body.id, body.state)
    return HttpResponse.json(getServiceAdministrationWorkspace())
  }),
]
