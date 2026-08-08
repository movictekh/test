import { beforeEach, describe, expect, it, vi } from 'vitest'

import { serviceAdministrationBackendApi } from './service-administration.backend-api'
import { runLiveServiceSetup } from './service-setup.orchestrator'
import type {
  CreateServiceStageAccess,
  CreateServiceWizardInput,
} from '../types/service-administration.types'

const input: CreateServiceWizardInput = {
  name: 'Boundary Survey',
  categoryId: 1,
  code: 'SUR-001',
  division: 'Land Surveying & Geospatial',
  description: 'Boundary survey',
  owner: '',
  ownerRoleId: null,
  slaDays: 5,
  fulfilmentMode: 'Managed service case',
  status: 'draft',
  clientVisibility: 'visible',
  branchNames: ['Enugu'],
  branchIds: [2],
  subservices: ['Standard'],
  pricing: {
    method: 'Unit rate',
    rate: 150000,
    depositPercent: 70,
    taxPercent: 7.5,
    discountApprovalPercent: 5,
  },
  requestFields: ['Location / site'],
  workflowStages: ['Review', 'Execution'],
}

const none: CreateServiceStageAccess = {
  subservices: false,
  pricing: false,
  requestForm: false,
  workflow: false,
  branches: false,
  publish: false,
  ownerRoles: false,
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(serviceAdministrationBackendApi, 'createService').mockResolvedValue({ id: 9 } as never)
})

describe('live Service setup orchestrator', () => {
  it('runs only permission-authorized stages', async () => {
    const pricing = vi
      .spyOn(serviceAdministrationBackendApi, 'createPricingConfig')
      .mockResolvedValue({ id: 3 } as never)
    const form = vi.spyOn(serviceAdministrationBackendApi, 'createRequestForm')
    await runLiveServiceSetup(
      { ...input, enabledStages: ['pricing', 'request-form'] },
      { ...none, pricing: true },
    )
    expect(pricing).toHaveBeenCalledTimes(1)
    expect(form).not.toHaveBeenCalled()
  })

  it('continues after an independent nested stage fails', async () => {
    vi.spyOn(serviceAdministrationBackendApi, 'createPricingConfig').mockRejectedValue(
      new Error('Pricing rejected'),
    )
    const form = vi
      .spyOn(serviceAdministrationBackendApi, 'createRequestForm')
      .mockResolvedValue({ id: 4 } as never)
    const workflow = vi
      .spyOn(serviceAdministrationBackendApi, 'createWorkflow')
      .mockResolvedValue({ id: 5 } as never)
    const branches = vi
      .spyOn(serviceAdministrationBackendApi, 'upsertBranchActivations')
      .mockResolvedValue([])
    const result = await runLiveServiceSetup(
      { ...input, enabledStages: ['pricing', 'request-form', 'workflow', 'branches'] },
      { ...none, pricing: true, requestForm: true, workflow: true, branches: true },
    )
    expect(form).toHaveBeenCalledTimes(1)
    expect(workflow).toHaveBeenCalledTimes(1)
    expect(branches).toHaveBeenCalledWith(
      9,
      expect.arrayContaining([expect.objectContaining({ branch_id: 2 })]),
    )
    expect(result.stages).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: 'pricing', state: 'failed' }),
        expect.objectContaining({ id: 'request-form', state: 'success' }),
        expect.objectContaining({ id: 'workflow', state: 'success' }),
        expect.objectContaining({ id: 'branches', state: 'success' }),
      ]),
    )
  })

  it('retries failed stages without recreating the Service core', async () => {
    const create = vi.spyOn(serviceAdministrationBackendApi, 'createService')
    const form = vi
      .spyOn(serviceAdministrationBackendApi, 'createRequestForm')
      .mockResolvedValue({ id: 4 } as never)
    await runLiveServiceSetup(
      input,
      { ...none, requestForm: true },
      { existingServiceId: 9, onlyStages: ['request-form'] },
    )
    expect(create).not.toHaveBeenCalled()
    expect(form).toHaveBeenCalledTimes(1)
  })

  it('publishes only after backend readiness stages succeed', async () => {
    vi.spyOn(serviceAdministrationBackendApi, 'createPricingConfig').mockResolvedValue({
      id: 3,
    } as never)
    vi.spyOn(serviceAdministrationBackendApi, 'createRequestForm').mockResolvedValue({
      id: 4,
    } as never)
    vi.spyOn(serviceAdministrationBackendApi, 'upsertBranchActivations').mockResolvedValue([])
    vi.spyOn(serviceAdministrationBackendApi, 'getCatalogueDetail').mockResolvedValue({
      active_request_form_id: 4,
      active_pricing_config_id: 3,
      active_workflow_id: null,
    } as never)
    const publish = vi
      .spyOn(serviceAdministrationBackendApi, 'publishService')
      .mockResolvedValue({ id: 9 } as never)
    await runLiveServiceSetup(
      {
        ...input,
        status: 'active',
        enabledStages: ['pricing', 'request-form', 'branches', 'publish'],
      },
      { ...none, pricing: true, requestForm: true, branches: true, publish: true },
    )
    expect(publish).toHaveBeenCalledWith(
      9,
      expect.objectContaining({ status: 'active', request_form_id: 4, pricing_config_id: 3 }),
    )
  })
})
