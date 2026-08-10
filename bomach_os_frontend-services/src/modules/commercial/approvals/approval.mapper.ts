import type {
  ApprovalActionTypeOption,
  ApprovalDecision,
  ApprovalFlow,
  ApprovalRequest,
  PaginatedApprovalFlows,
  PaginatedApprovalRequests,
} from './approval.types'

type R = Record<string, unknown>
const rec = (v: unknown): R =>
  typeof v === 'object' && v !== null && !Array.isArray(v) ? (v as R) : {}
const txt = (v: unknown, f = '') => (typeof v === 'string' ? v : f)
const num = (v: unknown, f = 0) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : f
}
const nnum = (v: unknown) => (v == null || v === '' ? null : num(v))
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
function rows(payload: unknown) {
  if (Array.isArray(payload)) return { count: payload.length, rows: payload }
  const r = rec(payload)
  const items = Array.isArray(r.items)
    ? r.items
    : Array.isArray(r.results)
      ? r.results
      : Array.isArray(r.data)
        ? r.data
        : []
  return { count: num(r.count, items.length), rows: items }
}

export function mapApprovalDecision(payload: unknown): ApprovalDecision {
  const v = rec(payload)
  return {
    id: num(v.id),
    stepOrder: num(v.step_order),
    stepName: txt(v.step_name),
    decision: txt(v.decision, 'approved') as ApprovalDecision['decision'],
    decisionDisplay: txt(v.decision_display, txt(v.decision)),
    comment: txt(v.comment),
    approverId: nnum(v.approver_id),
    approverName: txt(v.approver_name),
    createdAt: txt(v.created_at),
  }
}

export function mapApprovalRequest(payload: unknown): ApprovalRequest {
  const v = rec(payload)
  return {
    id: num(v.id),
    approvalRequestId: txt(v.approval_request_id),
    flowId: num(v.flow_id),
    flowName: txt(v.flow_name),
    actionType: txt(v.action_type),
    actionTypeDisplay: txt(v.action_type_display, txt(v.action_type)),
    title: txt(v.title),
    description: txt(v.description),
    status: txt(v.status, 'pending') as ApprovalRequest['status'],
    statusDisplay: txt(v.status_display, txt(v.status)),
    currentStep: num(v.current_step, 1),
    totalSteps: num(v.total_steps, 1),
    pendingStepName: txt(v.pending_step_name),
    pendingStepRequiredLevel: txt(v.pending_step_required_level),
    pendingStepRequiredLevelDisplay: txt(v.pending_step_required_level_display),
    decisions: arr(v.decisions).map(mapApprovalDecision),
    metadata: rec(v.metadata),
    createdById: nnum(v.created_by_id),
    createdByName: txt(v.created_by_name),
    createdAt: txt(v.created_at),
    updatedAt: txt(v.updated_at),
  }
}

export function mapApprovalRequestList(payload: unknown): PaginatedApprovalRequests {
  const result = rows(payload)
  return { count: result.count, items: result.rows.map(mapApprovalRequest) }
}

export function mapApprovalFlow(payload: unknown): ApprovalFlow {
  const v = rec(payload)
  return {
    id: num(v.id),
    name: txt(v.name),
    description: txt(v.description),
    actionType: txt(v.action_type),
    actionTypeDisplay: txt(v.action_type_display, txt(v.action_type)),
    isActive: Boolean(v.is_active),
    steps: arr(v.steps).map((payload) => {
      const step = rec(payload)
      return {
        id: num(step.id),
        stepOrder: num(step.step_order),
        stepName: txt(step.step_name),
        requiredLevel: txt(step.required_level),
        requiredLevelDisplay: txt(step.required_level_display, txt(step.required_level)),
      }
    }),
    createdById: nnum(v.created_by_id),
    createdByName: txt(v.created_by_name),
    createdAt: txt(v.created_at),
    updatedAt: txt(v.updated_at),
  }
}

export function mapApprovalFlowList(payload: unknown): PaginatedApprovalFlows {
  const result = rows(payload)
  return { count: result.count, items: result.rows.map(mapApprovalFlow) }
}

export function mapApprovalActionTypes(payload: unknown): ApprovalActionTypeOption[] {
  return arr(rec(payload).action_types)
    .map((payload) => {
      const row = rec(payload)
      return { value: txt(row.value), label: txt(row.label) }
    })
    .filter((item) => item.value && item.label)
}
