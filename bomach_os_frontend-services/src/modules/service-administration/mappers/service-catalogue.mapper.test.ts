import { describe, expect, it } from 'vitest'

import type {
  ServiceCatalogueCardDto,
  ServiceCatalogueDetailDto,
} from '../api/service-administration.contracts'
import { mapServiceCatalogueCard, mapServiceCatalogueDetail } from './service-catalogue.mapper'

const card: ServiceCatalogueCardDto = {
  id: 9,
  code: 'SUR-001',
  name: 'Boundary Survey',
  category_id: 1,
  category_name: 'Surveying',
  division: 'Land Surveying & Geospatial',
  description: 'Boundary survey service',
  base_price: '150000.00',
  delivery_time: '5 days',
  status: 'active',
  owner_role_id: 3,
  owner_role_name: 'Service Manager',
  default_sla_days: 5,
  fulfillment_mode: 'managed_case',
  client_visibility: 'visible',
  active_request_form_id: 10,
  active_pricing_config_id: 11,
  active_workflow_id: 12,
  subservice_count: 2,
  branch_activation_count: 1,
  created_at: '2026-08-08T00:00:00Z',
  updated_at: '2026-08-08T00:00:00Z',
  created_by_id: 1,
  active_request_form: {
    id: 10,
    service_id: 9,
    name: 'Survey Request',
    version: 1,
    status: 'active',
    is_active: true,
    field_count: 1,
    created_by_id: 1,
    created_at: '2026-08-08T00:00:00Z',
    updated_at: '2026-08-08T00:00:00Z',
  },
  active_pricing_config: {
    id: 11,
    service_id: 9,
    service_name: 'Boundary Survey',
    name: 'Survey Pricing',
    version: 1,
    pricing_type: 'fixed',
    formula: '',
    tax_rate: '0.00',
    deposit_percent: '70.00',
    discount_approval_threshold_percent: '5.00',
    status: 'active',
    is_active: true,
    field_count: 0,
    created_by_id: 1,
    created_at: '2026-08-08T00:00:00Z',
    updated_at: '2026-08-08T00:00:00Z',
  },
  active_workflow: {
    id: 12,
    service_id: 9,
    name: 'Survey Workflow',
    version: 1,
    status: 'active',
    is_active: true,
    stage_count: 2,
    created_by_id: 1,
    created_at: '2026-08-08T00:00:00Z',
    updated_at: '2026-08-08T00:00:00Z',
  },
  active_branches: [
    {
      id: 20,
      service_id: 9,
      branch_id: 2,
      branch_name: 'Enugu',
      status: 'active',
      client_visible: true,
      capacity: 4,
      activated_at: null,
      created_at: '2026-08-08T00:00:00Z',
      updated_at: '2026-08-08T00:00:00Z',
    },
  ],
}

describe('service catalogue mapper', () => {
  it('maps a catalogue card into the existing UI domain model', () => {
    expect(mapServiceCatalogueCard(card)).toMatchObject({
      id: '9',
      code: 'SUR-001',
      name: 'Boundary Survey',
      owner: 'Service Manager',
      branchNames: ['Enugu'],
      calculatorName: 'Survey Pricing',
      requestFormName: 'Survey Request',
      workflowName: 'Survey Workflow',
      readiness: 100,
      slaDays: 5,
      fulfilmentMode: 'managed_case',
    })
  })

  it('uses the real backend publish requirements for readiness', () => {
    const missingPricing: ServiceCatalogueCardDto = {
      ...card,
      active_pricing_config_id: null,
      active_pricing_config: null,
    }

    expect(mapServiceCatalogueCard(missingPricing).readiness).toBe(67)
  })

  it('does not require workflow for backend publish readiness', () => {
    const noWorkflow: ServiceCatalogueCardDto = {
      ...card,
      active_workflow_id: null,
      active_workflow: null,
    }

    expect(mapServiceCatalogueCard(noWorkflow).readiness).toBe(100)
  })

  it('maps ordered detail configuration data', () => {
    const detail: ServiceCatalogueDetailDto = {
      ...card,
      subservices: [
        {
          id: 2,
          service_id: 9,
          code: 'b',
          name: 'Second',
          description: '',
          status: 'active',
          default_sla_days: 1,
          sort_order: 2,
          created_at: '2026-08-08T00:00:00Z',
          updated_at: '2026-08-08T00:00:00Z',
        },
        {
          id: 1,
          service_id: 9,
          code: 'a',
          name: 'First',
          description: '',
          status: 'active',
          default_sla_days: 1,
          sort_order: 1,
          created_at: '2026-08-08T00:00:00Z',
          updated_at: '2026-08-08T00:00:00Z',
        },
      ],
      request_forms: [],
      pricing_configs: [],
      workflows: [],
      branch_activations: [],
      active_request_form: {
        ...card.active_request_form!,
        fields: [
          {
            id: 1,
            form_id: 10,
            key: 'location',
            label: 'Location',
            field_type: 'location',
            required: true,
            options: [],
            validation: {},
            help_text: '',
            placeholder: '',
            sort_order: 0,
          },
        ],
      },
      active_workflow: {
        ...card.active_workflow!,
        stages: [
          {
            id: 2,
            workflow_id: 12,
            name: 'Execution',
            owner_role_id: null,
            owner_role_name: '',
            sla_days: 2,
            requires_approval: false,
            requires_evidence: true,
            client_visible: true,
            sort_order: 2,
          },
          {
            id: 1,
            workflow_id: 12,
            name: 'Review',
            owner_role_id: null,
            owner_role_name: '',
            sla_days: 1,
            requires_approval: false,
            requires_evidence: false,
            client_visible: true,
            sort_order: 1,
          },
        ],
      },
    }

    expect(mapServiceCatalogueDetail(detail)).toMatchObject({
      subservices: ['First', 'Second'],
      requestFields: ['Location'],
      workflowStages: ['Review', 'Execution'],
    })
  })
})
