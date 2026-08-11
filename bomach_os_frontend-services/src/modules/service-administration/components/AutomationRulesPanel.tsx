import { IconBolt } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { useAuth } from '@/app/auth'
import { hasPermission, PERMISSIONS } from '@/app/permissions'
import { presentError } from '@/shared/errors'
import { Button } from '@/shared/ui/button'
import { EmptyState } from '@/shared/ui/empty-state'
import { useToast } from '@/shared/ui'

import { workflowRulesApi } from '../api/workflow-rules.api'
import { workflowRuleKeys, workflowRuleQueries } from '../api/workflow-rules.queries'
import type {
  SaveWorkflowRuleInput,
  WorkflowAutomationRule,
  WorkflowRuleRecipient,
} from '../api/workflow-rules.types'

const operators = [
  ['eq', 'Equals'],
  ['neq', 'Does not equal'],
  ['gt', 'Greater than'],
  ['gte', 'Greater than or equal'],
  ['lt', 'Less than'],
  ['lte', 'Less than or equal'],
  ['contains', 'Contains'],
] as const
const EMPTY_RECIPIENTS: WorkflowRuleRecipient[] = []

function configText(rule: WorkflowAutomationRule, key: string): string {
  const value = rule.actionConfig[key]
  return typeof value === 'string' ? value : ''
}

function recipientIds(rule: WorkflowAutomationRule | null): number[] {
  const value = rule?.actionConfig.recipient_ids
  return Array.isArray(value)
    ? value.map((item) => Number(item)).filter((item) => Number.isInteger(item) && item > 0)
    : []
}

function recipientLabel(recipient: WorkflowRuleRecipient): string {
  const secondary = [recipient.designation, recipient.roleName].filter(Boolean).join(' · ')
  return secondary ? `${recipient.name} · ${secondary}` : recipient.name
}

export function AutomationRulesPanel() {
  const { user } = useAuth()
  const toast = useToast()
  const queryClient = useQueryClient()

  const canList = hasPermission(user, PERMISSIONS.workflowRulesList)
  const canView = hasPermission(user, PERMISSIONS.workflowRulesView)
  const canCreate = hasPermission(user, PERMISSIONS.workflowRulesCreate)
  const canUpdate = hasPermission(user, PERMISSIONS.workflowRulesUpdate)
  const canDelete = hasPermission(user, PERMISSIONS.workflowRulesDelete)

  const rulesQuery = useQuery({
    ...workflowRuleQueries.list(),
    enabled: canList,
  })

  const triggersQuery = useQuery({
    ...workflowRuleQueries.triggers(),
    enabled: canView,
  })

  const actionsQuery = useQuery({
    ...workflowRuleQueries.actions(),
    enabled: canView,
  })

  const [editingRule, setEditingRule] = useState<WorkflowAutomationRule | 'new' | null>(null)

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: workflowRuleKeys.all })
  }

  const saveRule = useMutation({
    mutationFn: (input: SaveWorkflowRuleInput) =>
      input.id ? workflowRulesApi.update(input) : workflowRulesApi.create(input),
    onSuccess: async () => {
      await invalidate()
      setEditingRule(null)
      toast.success('Automation rule saved')
    },
    onError: (error) => {
      toast.error('Automation rule could not be saved', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  const deactivateRule = useMutation({
    mutationFn: (ruleId: number) => workflowRulesApi.deactivate(ruleId),
    onSuccess: async () => {
      await invalidate()
      toast.success('Automation rule deactivated')
    },
    onError: (error) => {
      toast.error('Automation rule could not be deactivated', {
        description: presentError(error, 'background-action').message,
      })
    },
  })

  return (
    <div className="service-admin-card">
      <div className="service-admin-card-header">
        <div>
          <div className="service-admin-card-title">Automation Rules</div>
          <div className="service-admin-card-subtitle">
            Automation rules that apply across service operations.
          </div>
        </div>

        {canCreate ? (
          <button
            type="button"
            className="service-admin-button service-admin-button-small"
            onClick={() => setEditingRule('new')}
          >
            Add Rule
          </button>
        ) : null}
      </div>

      {!canList ? (
        <EmptyState
          title="Automation Rules unavailable"
          description="You do not currently have access to view automation rules."
        />
      ) : rulesQuery.isPending ? (
        <div className="service-admin-card-subtitle py-5">Loading automation rules...</div>
      ) : rulesQuery.isError ? (
        <EmptyState
          title="Automation Rules unavailable"
          description={presentError(rulesQuery.error, 'section-load').message}
          action={
            <Button variant="outline" size="sm" onClick={() => void rulesQuery.refetch()}>
              Retry
            </Button>
          }
        />
      ) : (rulesQuery.data ?? []).length === 0 ? (
        <EmptyState
          title="No automation rules"
          description="Automation rules will appear here once the first rule is created."
        />
      ) : (
        (rulesQuery.data ?? []).map((rule) => (
          <div key={rule.id} className="service-admin-list-row">
            <div className="service-admin-list-ico service-admin-list-ico--bolt">
              <IconBolt size={16} aria-hidden="true" />
            </div>
            <div className="service-admin-list-meta">
              <div className="service-admin-list-name">{rule.name}</div>
              <div className="service-admin-list-sub">
                {rule.description || `${rule.triggerEvent} -> ${rule.actionType}`}
                {' · '}
                {rule.executionCount} execution(s)
              </div>
            </div>

            <span
              className={`service-admin-pill ${
                rule.active ? 'service-admin-pill-green' : 'service-admin-pill-gray'
              }`}
            >
              {rule.active ? 'Active' : 'Inactive'}
            </span>

            <div className="service-admin-acts">
              {canUpdate ? (
                <button
                  type="button"
                  className="service-admin-button service-admin-button-small"
                  onClick={() => setEditingRule(rule)}
                >
                  Edit
                </button>
              ) : null}

              {canDelete && rule.active ? (
                <button
                  type="button"
                  className="service-admin-button service-admin-button-small"
                  disabled={deactivateRule.isPending}
                  onClick={() => deactivateRule.mutate(rule.id)}
                >
                  Deactivate
                </button>
              ) : null}
            </div>
          </div>
        ))
      )}

      {editingRule ? (
        <RuleEditor
          rule={editingRule === 'new' ? null : editingRule}
          triggerChoices={triggersQuery.data ?? []}
          actionChoices={actionsQuery.data ?? []}
          pending={saveRule.isPending}
          onClose={() => setEditingRule(null)}
          onSave={(input) => saveRule.mutate(input)}
        />
      ) : null}
    </div>
  )
}

function RuleEditor({
  rule,
  triggerChoices,
  actionChoices,
  pending,
  onClose,
  onSave,
}: {
  rule: WorkflowAutomationRule | null
  triggerChoices: Array<{ value: string; label: string }>
  actionChoices: Array<{ value: string; label: string }>
  pending: boolean
  onClose: () => void
  onSave: (input: SaveWorkflowRuleInput) => void
}) {
  const firstCondition = rule?.conditions[0]

  const [name, setName] = useState(rule?.name ?? '')
  const [description, setDescription] = useState(rule?.description ?? '')
  const [trigger, setTrigger] = useState(
    rule?.triggerEvent ?? triggerChoices[0]?.value ?? 'service_order_status_changed',
  )
  const [field, setField] = useState(firstCondition?.field ?? 'order_status')
  const [operator, setOperator] = useState(firstCondition?.operator ?? 'eq')
  const [conditionValue, setConditionValue] = useState(firstCondition?.value ?? '')
  const [action, setAction] = useState(
    rule?.actionType ?? actionChoices[0]?.value ?? 'send_notification',
  )
  const [selectedRecipientIds, setSelectedRecipientIds] = useState<number[]>(recipientIds(rule))
  const [recipientSearch, setRecipientSearch] = useState('')
  const [title, setTitle] = useState(rule ? configText(rule, 'title') : '')
  const [message, setMessage] = useState(rule ? configText(rule, 'message') : '')
  const [link, setLink] = useState(rule ? configText(rule, 'link') : '')
  const [active, setActive] = useState(rule?.active ?? true)
  const [error, setError] = useState('')
  const recipientsQuery = useQuery({
    ...workflowRuleQueries.recipients(recipientSearch),
    enabled: action === 'send_notification',
  })
  const availableRecipients = recipientsQuery.data ?? EMPTY_RECIPIENTS
  const selectedRecipients = useMemo(
    () =>
      selectedRecipientIds
        .map((id) => availableRecipients.find((item) => item.userId === id))
        .filter(Boolean),
    [availableRecipients, selectedRecipientIds],
  )
  const unknownSelectedRecipientIds = selectedRecipientIds.filter(
    (id) => !availableRecipients.some((item) => item.userId === id),
  )

  const toggleRecipient = (userId: number) => {
    setSelectedRecipientIds((current) =>
      current.includes(userId) ? current.filter((id) => id !== userId) : [...current, userId],
    )
  }

  const submit = () => {
    if (!name.trim()) return setError('Rule name is required.')
    if (!trigger) return setError('Trigger is required.')
    if (!field.trim()) return setError('Condition field is required.')
    if (!conditionValue.trim()) return setError('Condition value is required.')
    if (!action) return setError('Action is required.')
    if (selectedRecipientIds.length === 0) {
      return setError('Select at least one recipient.')
    }
    if (!title.trim()) return setError('Notification title is required.')
    if (!message.trim()) return setError('Notification message is required.')

    setError('')
    onSave({
      ...(rule ? { id: rule.id } : {}),
      name: name.trim(),
      description: description.trim(),
      triggerEvent: trigger,
      conditions: [
        {
          field: field.trim(),
          operator,
          value: conditionValue.trim(),
        },
      ],
      actionType: action,
      actionConfig: {
        recipient_ids: selectedRecipientIds,
        title: title.trim(),
        message: message.trim(),
        ...(link.trim() ? { link: link.trim() } : {}),
      },
      active,
    })
  }

  return (
    <div className="service-admin-editor-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="service-admin-field-editor-modal service-admin-rule-modal"
        role="dialog"
        aria-modal="true"
        aria-label={rule ? 'Edit Automation Rule' : 'Create Automation Rule'}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <h2>{rule ? 'Edit Automation Rule' : 'Create Automation Rule'}</h2>
            <p>Set the trigger, recipients, and message for this rule.</p>
          </div>
          <button
            type="button"
            className="service-admin-stage-editor-close"
            aria-label="Close"
            onClick={onClose}
          >
            ×
          </button>
        </header>

        <div className="service-admin-field-editor-body">
          {error ? (
            <div className="service-admin-notice service-admin-notice-red">{error}</div>
          ) : null}

          <div className="service-admin-rule-sections">
            <section className="service-admin-rule-section">
              <div className="service-admin-rule-section-title">Rule setup</div>
              <div className="service-admin-form-grid">
                <label className="service-admin-config-field service-admin-config-field--full">
                  <span>Rule name</span>
                  <input value={name} onChange={(event) => setName(event.target.value)} />
                </label>

                <label className="service-admin-config-field">
                  <span>Trigger</span>
                  <select
                    value={trigger}
                    onChange={(event) => {
                      const value = event.target.value
                      setTrigger(value)
                      setField(value === 'service_order_status_changed' ? 'order_status' : 'status')
                    }}
                  >
                    {triggerChoices.map((choice) => (
                      <option key={choice.value} value={choice.value}>
                        {choice.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="service-admin-config-field">
                  <span>Status</span>
                  <select
                    value={active ? 'active' : 'inactive'}
                    onChange={(event) => setActive(event.target.value === 'active')}
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </label>

                <label className="service-admin-config-field">
                  <span>Condition field</span>
                  <input value={field} onChange={(event) => setField(event.target.value)} />
                </label>

                <label className="service-admin-config-field">
                  <span>Operator</span>
                  <select value={operator} onChange={(event) => setOperator(event.target.value)}>
                    {operators.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="service-admin-config-field service-admin-config-field--full">
                  <span>Condition value</span>
                  <input
                    value={conditionValue}
                    onChange={(event) => setConditionValue(event.target.value)}
                    placeholder={field === 'order_status' ? 'completed' : 'sent'}
                  />
                </label>

                <label className="service-admin-config-field service-admin-config-field--full">
                  <span>Description</span>
                  <textarea
                    rows={3}
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                  />
                </label>
              </div>
            </section>

            <section className="service-admin-rule-section">
              <div className="service-admin-rule-section-title">Notification</div>
              <div className="service-admin-form-grid">
                <label className="service-admin-config-field">
                  <span>Action</span>
                  <select value={action} onChange={(event) => setAction(event.target.value)}>
                    {actionChoices.map((choice) => (
                      <option key={choice.value} value={choice.value}>
                        {choice.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="service-admin-config-field service-admin-config-field--full">
                  <span>Recipients</span>
                  <input
                    value={recipientSearch}
                    onChange={(event) => setRecipientSearch(event.target.value)}
                    placeholder="Search by name, employee ID, or email"
                  />
                  <small>Select one or more people to receive this notification.</small>
                </label>

                {selectedRecipientIds.length > 0 ? (
                  <div className="service-admin-rule-chip-row service-admin-config-field--full">
                    {selectedRecipients.map((recipient) => (
                      <span key={recipient!.userId} className="service-admin-rule-chip">
                        {recipientLabel(recipient!)}
                        <button
                          type="button"
                          className="service-admin-rule-chip-remove"
                          aria-label={`Remove ${recipient!.name}`}
                          onClick={() => toggleRecipient(recipient!.userId)}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                    {unknownSelectedRecipientIds.map((value) => (
                      <span key={value} className="service-admin-rule-chip">
                        User ID {value}
                        <button
                          type="button"
                          className="service-admin-rule-chip-remove"
                          aria-label={`Remove user ID ${value}`}
                          onClick={() => toggleRecipient(value)}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                ) : null}

                <div className="service-admin-rule-recipient-list service-admin-config-field--full">
                  {recipientsQuery.isPending ? (
                    <div className="service-admin-card-subtitle">Loading recipients...</div>
                  ) : recipientsQuery.isError ? (
                    <div className="service-admin-card-subtitle">
                      Recipient directory is not available for this account.
                    </div>
                  ) : availableRecipients.length === 0 ? (
                    <div className="service-admin-card-subtitle">
                      No matching team members found.
                    </div>
                  ) : (
                    availableRecipients.map((recipient) => {
                      const checked = selectedRecipientIds.includes(recipient.userId)
                      return (
                        <button
                          key={recipient.userId}
                          type="button"
                          className={`service-admin-rule-recipient-option${
                            checked ? 'service-admin-rule-recipient-option--active' : ''
                          }`}
                          onClick={() => toggleRecipient(recipient.userId)}
                        >
                          <span className="service-admin-rule-recipient-name">
                            {recipient.name}
                          </span>
                          <span className="service-admin-rule-recipient-meta">
                            {recipient.employeeId}
                            {recipient.designation ? ` · ${recipient.designation}` : ''}
                            {recipient.roleName ? ` · ${recipient.roleName}` : ''}
                          </span>
                          <span className="service-admin-rule-recipient-email">
                            {recipient.email}
                          </span>
                        </button>
                      )
                    })
                  )}
                </div>

                <label className="service-admin-config-field service-admin-config-field--full">
                  <span>Notification title</span>
                  <input value={title} onChange={(event) => setTitle(event.target.value)} />
                </label>

                <label className="service-admin-config-field service-admin-config-field--full">
                  <span>Notification message</span>
                  <textarea
                    rows={4}
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                  />
                </label>

                <label className="service-admin-config-field service-admin-config-field--full">
                  <span>Notification link (optional)</span>
                  <input
                    value={link}
                    onChange={(event) => setLink(event.target.value)}
                    placeholder="/orders/123"
                  />
                </label>
              </div>
            </section>
          </div>
        </div>

        <footer>
          <button type="button" className="service-admin-button" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="service-admin-button service-admin-button-primary"
            disabled={pending}
            onClick={submit}
          >
            {pending ? 'Saving...' : rule ? 'Save Rule' : 'Create Rule'}
          </button>
        </footer>
      </section>
    </div>
  )
}
