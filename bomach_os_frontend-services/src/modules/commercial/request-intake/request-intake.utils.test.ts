import { describe, expect, it } from 'vitest'

import type { IntakeField, ServicePricingConfig } from '../api/service-requests.types'

import {
  calculateEstimateTotal,
  isBudgetField,
  normalizeAnswers,
  resolveAutoAnswer,
  shouldHideAutoField,
  validateAnswerFields,
} from './request-intake.utils'

const intakeField = (
  overrides: Partial<IntakeField> & Pick<IntakeField, 'key' | 'label' | 'fieldType'>,
): IntakeField => ({
  id: 1,
  required: false,
  options: [],
  validation: {},
  helpText: '',
  placeholder: '',
  sortOrder: 0,
  ...overrides,
})

const context = {
  contactName: 'Acme Limited',
  contactPhone: '08000000000',
  contactEmail: 'ops@acme.test',
  customerType: 'corporate',
  budget: 250000,
  preferredDate: '2026-08-20',
  uploads: [],
}

describe('request intake utilities', () => {
  it('preserves semantic auto-fill behavior', () => {
    const budget = intakeField({
      key: 'project_budget',
      label: 'Project Budget',
      fieldType: 'money',
    })

    expect(isBudgetField(budget)).toBe(true)
    expect(resolveAutoAnswer(budget, context)).toBe(250000)
    expect(shouldHideAutoField(budget, context)).toBe(true)
  })

  it('preserves required and numeric validation', () => {
    const fields = [
      intakeField({
        key: 'quantity',
        label: 'Quantity',
        fieldType: 'number',
        required: true,
      }),
    ]

    expect(validateAnswerFields(fields, { quantity: '' })).toEqual({
      quantity: 'Quantity is required.',
    })
    expect(validateAnswerFields(fields, { quantity: 'x' })).toEqual({
      quantity: 'Quantity must be numeric.',
    })
  })

  it('preserves backend answer normalization', () => {
    const fields = [
      intakeField({ key: 'quantity', label: 'Quantity', fieldType: 'number' }),
      intakeField({ key: 'urgent', label: 'Urgent', fieldType: 'checkbox' }),
      intakeField({ key: 'docs', label: 'Documents', fieldType: 'file' }),
    ]

    expect(
      normalizeAnswers(fields, {
        quantity: '4',
        urgent: true,
        docs: 'https://files.test/a.pdf',
      }),
    ).toEqual({
      quantity: 4,
      urgent: true,
      docs: ['https://files.test/a.pdf'],
    })
  })

  it('preserves conventional unit-rate pricing', () => {
    const pricing: ServicePricingConfig = {
      id: 1,
      serviceId: 2,
      serviceName: 'Survey',
      name: 'Unit pricing',
      version: 1,
      pricingType: 'unit_rate',
      formula: '',
      taxRate: 7.5,
      depositPercent: 0,
      discountApprovalThresholdPercent: 0,
      status: 'active',
      active: true,
      fieldCount: 2,
      fields: [
        {
          id: 1,
          key: 'quantity',
          label: 'Quantity',
          fieldType: 'number',
          defaultValue: null,
          required: true,
          options: [],
          validation: {},
          sortOrder: 0,
        },
        {
          id: 2,
          key: 'rate',
          label: 'Rate',
          fieldType: 'money',
          defaultValue: null,
          required: true,
          options: [],
          validation: {},
          sortOrder: 1,
        },
      ],
    }

    expect(
      calculateEstimateTotal(
        pricing,
        [
          intakeField({ key: 'quantity', label: 'Quantity', fieldType: 'number' }),
          intakeField({ key: 'rate', label: 'Rate', fieldType: 'money' }),
        ],
        { quantity: 2, rate: 1000 },
        context,
      ),
    ).toEqual({
      supported: true,
      subtotal: 2000,
      total: 2150,
    })
  })
})
