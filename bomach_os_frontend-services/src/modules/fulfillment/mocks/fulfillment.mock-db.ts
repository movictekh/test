import type {
  AddMilestoneInput,
  AddOrderUpdateInput,
  CreateDeliverableInput,
  DecideDeliverableInput,
  Deliverable,
  CreateExecutionTaskInput,
  CommercialOrderHandoffInput,
  CreateServiceOrderInput,
  ExecutionTask,
  FulfillmentWorkspace,
  OrderActivity,
  ServiceOrder,
  UpdateExecutionTaskInput,
  UpdateServiceOrderInput,
} from '../types/fulfillment.types'
import {
  advanceMilestones,
  clampProgress,
  nextTaskStatus,
  taskProgressForStatus,
  commercialSourceAlreadyOrdered,
  canCompleteOrderWithDeliverables,
} from '../workspaces/fulfillment-workflow.rules'
import { appendMockAuditEvent } from '@/shared/audit/mock-audit-store'

const nowIso = () => new Date().toISOString()
const today = () => new Date().toISOString().slice(0, 10)

function activity(
  id: string,
  at: string,
  title: string,
  actor: string,
  description: string,
): OrderActivity {
  return {
    id,
    at,
    title,
    actor,
    description,
    visibility: 'Internal and client',
  }
}

const orders: ServiceOrder[] = [
  {
    id: 'ORD-260713-004',
    requestId: 'REQ-260712-014',
    quotationId: 'Q-260712-008',
    invoiceId: 'INV-260713-004',
    client: 'Mrs Chioma Ugwu',
    service: 'Estate Plot Sales',
    division: 'Real Estate',
    mode: 'Transaction & allocation',
    status: 'Awaiting Client',
    progress: 62,
    owner: 'Property Manager',
    startAt: '2026-07-12',
    dueAt: '2026-07-18',
    value: 4500000,
    stage: 'Documentation',
    nextAction: 'Client to sign deed',
    paymentReady: true,
    milestones: [
      { id: 'M-400-1', name: 'Availability & reservation', status: 'Done' },
      { id: 'M-400-2', name: 'Payment confirmation', status: 'Done' },
      { id: 'M-400-3', name: 'Documentation', status: 'Active' },
      { id: 'M-400-4', name: 'Allocation', status: 'Pending' },
      { id: 'M-400-5', name: 'Handover', status: 'Pending' },
    ],
    activities: [
      activity(
        'OA-400-1',
        '2026-07-12T09:00:00.000Z',
        'Order created',
        'System',
        'Invoice fully paid.',
      ),
      activity(
        'OA-400-2',
        '2026-07-13T11:30:00.000Z',
        'Documents prepared',
        'Legal Officer',
        'Deed draft uploaded for client review.',
      ),
    ],
  },
  {
    id: 'ORD-260710-002',
    requestId: 'REQ-260710-022',
    quotationId: 'Q-260710-003',
    invoiceId: 'INV-260710-002',
    client: 'Apex Retail Ltd',
    service: 'Business Software Development',
    division: 'Information Technology',
    mode: 'Project',
    status: 'Active',
    progress: 24,
    owner: 'Project Manager',
    startAt: '2026-07-10',
    dueAt: '2026-10-30',
    value: 12000000,
    stage: 'Requirements',
    nextAction: 'Approve product specification',
    paymentReady: true,
    milestones: [
      { id: 'M-200-1', name: 'Discovery', status: 'Done' },
      { id: 'M-200-2', name: 'Requirements', status: 'Active' },
      { id: 'M-200-3', name: 'Design', status: 'Pending' },
      { id: 'M-200-4', name: 'Development', status: 'Pending' },
      { id: 'M-200-5', name: 'QA', status: 'Pending' },
      { id: 'M-200-6', name: 'Deployment', status: 'Pending' },
    ],
    activities: [
      activity(
        'OA-200-1',
        '2026-07-10T10:00:00.000Z',
        'Project created',
        'System',
        'Mobilisation threshold met.',
      ),
      activity(
        'OA-200-2',
        '2026-07-12T15:00:00.000Z',
        'Workshop held',
        'Business Analyst',
        'Requirements workshop completed.',
      ),
    ],
  },
  {
    id: 'ORD-260701-019',
    requestId: 'REQ-260625-008',
    client: 'Greenview Cooperative',
    service: 'Cadastral Land Survey',
    division: 'Land Surveying & Geospatial',
    mode: 'Service order',
    status: 'Quality Review',
    progress: 78,
    owner: 'Land Surveyor',
    startAt: '2026-07-01',
    dueAt: '2026-07-15',
    value: 3200000,
    stage: 'Plan Review',
    nextAction: 'Chief Surveyor approval',
    paymentReady: true,
    milestones: [
      { id: 'M-019-1', name: 'Document review', status: 'Done' },
      { id: 'M-019-2', name: 'Field survey', status: 'Done' },
      { id: 'M-019-3', name: 'Processing', status: 'Done' },
      { id: 'M-019-4', name: 'Professional review', status: 'Active' },
      { id: 'M-019-5', name: 'Delivery', status: 'Pending' },
    ],
    activities: [
      activity(
        'OA-019-1',
        '2026-07-01T09:00:00.000Z',
        'Order started',
        'Land Surveyor',
        'Documents checked.',
      ),
      activity(
        'OA-019-2',
        '2026-07-06T16:00:00.000Z',
        'Field survey completed',
        'Survey Team',
        'Coordinates and beacons captured.',
      ),
      activity(
        'OA-019-3',
        '2026-07-12T12:00:00.000Z',
        'Plan submitted',
        'Land Surveyor',
        'Draft plan submitted for review.',
      ),
    ],
  },
  {
    id: 'ORD-260630-011',
    requestId: 'REQ-260629-004',
    client: 'Noble Homes Ltd',
    service: 'Building Construction',
    division: 'Engineering & Construction',
    mode: 'Project & worksite',
    status: 'Active',
    progress: 47,
    owner: 'Project Manager',
    startAt: '2026-06-30',
    dueAt: '2026-11-30',
    value: 245000000,
    stage: 'Substructure',
    nextAction: 'Approve first-floor concrete pour',
    paymentReady: true,
    milestones: [
      { id: 'M-011-1', name: 'Mobilisation', status: 'Done' },
      { id: 'M-011-2', name: 'Site setup', status: 'Done' },
      { id: 'M-011-3', name: 'Foundation', status: 'Done' },
      { id: 'M-011-4', name: 'Substructure', status: 'Active' },
      { id: 'M-011-5', name: 'Superstructure', status: 'Pending' },
      { id: 'M-011-6', name: 'Roofing', status: 'Pending' },
    ],
    activities: [
      activity(
        'OA-011-1',
        '2026-06-30T08:00:00.000Z',
        'Project activated',
        'Head of Operations',
        'Contract and mobilisation confirmed.',
      ),
      activity(
        'OA-011-2',
        '2026-07-13T14:00:00.000Z',
        'Inspection request',
        'Site Engineer',
        'First-floor reinforcement ready for inspection.',
      ),
    ],
  },
  {
    id: 'ORD-260712-033',
    requestId: 'REQ-260712-030',
    client: 'Benji Vendor Network',
    service: 'Express Delivery',
    division: 'Courier & Logistics',
    mode: 'Quick service order',
    status: 'Completed',
    progress: 100,
    owner: 'Rider EN-04',
    startAt: '2026-07-12',
    dueAt: '2026-07-12',
    value: 8500,
    stage: 'Delivered',
    nextAction: 'Collect feedback',
    paymentReady: true,
    milestones: [
      { id: 'M-033-1', name: 'Pickup', status: 'Done' },
      { id: 'M-033-2', name: 'Transit', status: 'Done' },
      { id: 'M-033-3', name: 'Delivery', status: 'Done' },
    ],
    activities: [
      activity(
        'OA-033-1',
        '2026-07-12T08:30:00.000Z',
        'Order created',
        'System',
        'Delivery request paid.',
      ),
      activity(
        'OA-033-2',
        '2026-07-12T16:45:00.000Z',
        'Delivered',
        'Rider EN-04',
        'Proof of delivery uploaded.',
      ),
    ],
  },
]

const tasks: ExecutionTask[] = [
  {
    id: 'TSK-701',
    title: 'Schedule Ezeagu site assessment',
    orderId: 'REQ-260713-001',
    stageName: 'Site Assessment',
    status: 'To Do',
    owner: 'Civil Engineer',
    dueAt: '2026-07-14',
    priority: 'High',
    evidenceRequired: true,
    instructions: 'Confirm site access and assessment schedule.',
    progress: 0,
    evidence: [],
    activities: [
      {
        id: 'TASK-SEED-1',
        at: '2026-07-13T09:00:00.000Z',
        title: 'Task created',
        actor: 'Service Manager',
        description: 'Task created from fulfillment workflow.',
      },
    ],
  },
  {
    id: 'TSK-702',
    title: 'Verify Fortress plot 39 availability',
    orderId: 'REQ-260712-014',
    stageName: 'Availability & reservation',
    status: 'In Progress',
    owner: 'Property Manager',
    dueAt: '2026-07-13',
    priority: 'High',
    evidenceRequired: false,
    instructions: 'Confirm inventory and reservation position.',
    progress: 45,
    evidence: [],
    activities: [
      {
        id: 'TASK-SEED-2',
        at: '2026-07-13T09:00:00.000Z',
        title: 'Task created',
        actor: 'Service Manager',
        description: 'Task created from fulfillment workflow.',
      },
    ],
  },
  {
    id: 'TSK-703',
    title: 'Review Greenview survey plan',
    orderId: 'ORD-260701-019',
    stageName: 'Professional review',
    status: 'Review',
    owner: 'Chief Surveyor',
    dueAt: '2026-07-14',
    priority: 'Normal',
    evidenceRequired: true,
    instructions: 'Review draft plan before delivery.',
    progress: 85,
    evidence: [],
    activities: [
      {
        id: 'TASK-SEED-3',
        at: '2026-07-13T09:00:00.000Z',
        title: 'Task created',
        actor: 'Service Manager',
        description: 'Task created from fulfillment workflow.',
      },
    ],
  },
  {
    id: 'TSK-704',
    title: 'Prepare Apex product specification',
    orderId: 'ORD-260710-002',
    stageName: 'Requirements',
    status: 'In Progress',
    owner: 'Business Analyst',
    dueAt: '2026-07-16',
    priority: 'Normal',
    evidenceRequired: true,
    instructions: 'Prepare specification from approved requirements.',
    progress: 55,
    evidence: [],
    activities: [
      {
        id: 'TASK-SEED-4',
        at: '2026-07-13T09:00:00.000Z',
        title: 'Task created',
        actor: 'Service Manager',
        description: 'Task created from fulfillment workflow.',
      },
    ],
  },
  {
    id: 'TSK-705',
    title: 'Upload delivery proof',
    orderId: 'ORD-260712-033',
    stageName: 'Delivery',
    status: 'Done',
    owner: 'Rider EN-04',
    dueAt: '2026-07-12',
    priority: 'Normal',
    evidenceRequired: true,
    instructions: 'Attach recipient proof of delivery.',
    progress: 100,
    evidence: [],
    activities: [
      {
        id: 'TASK-SEED-5',
        at: '2026-07-13T09:00:00.000Z',
        title: 'Task created',
        actor: 'Service Manager',
        description: 'Task created from fulfillment workflow.',
      },
    ],
  },
]

const deliverables: Deliverable[] = [
  {
    id: 'DEL-701',
    orderId: 'ORD-260701-019',
    title: 'Greenview cadastral survey plan',
    type: 'Survey Plan',
    version: 'v2',
    owner: 'Land Surveyor',
    status: 'Under Review',
    clientVisible: true,
    date: '2026-07-12',
    approvalMode: 'Supervisor approval',
    fileName: 'greenview-survey-plan-v2.pdf',
  },
  {
    id: 'DEL-702',
    orderId: 'ORD-260712-033',
    title: 'Proof of delivery',
    type: 'Progress Evidence',
    version: 'v1',
    owner: 'Rider EN-04',
    status: 'Approved',
    clientVisible: true,
    date: '2026-07-12',
    approvalMode: 'No approval',
    fileName: 'pod-260712-033.jpg',
  },
]

function summary(): FulfillmentWorkspace['summary'] {
  const openStatuses = new Set([
    'Pending Mobilisation',
    'Active',
    'Quality Review',
    'Awaiting Client',
  ])
  const dueCutoff = new Date()
  dueCutoff.setDate(dueCutoff.getDate() + 7)

  return {
    activeOrders: orders.filter((order) => openStatuses.has(order.status)).length,
    dueSoon: orders.filter((order) => {
      const due = new Date(order.dueAt)
      return order.status !== 'Completed' && due <= dueCutoff
    }).length,
    awaitingClient: orders.filter((order) => order.status === 'Awaiting Client').length,
    completed: orders.filter((order) => order.status === 'Completed').length,
    openTasks: tasks.filter((task) => task.status !== 'Done').length,
    blockedTasks: tasks.filter((task) => task.status === 'Blocked').length,
  }
}

export function getFulfillmentWorkspace(): FulfillmentWorkspace {
  return {
    summary: summary(),
    orders,
    tasks,
    deliverables,
  }
}

export function ensureMockOrderFromCommercialSource(
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

  const created = orders.find((order) => order.invoiceId === input.invoiceId)
  if (created) {
    appendMockAuditEvent({
      area: 'Order',
      action: `Created ${created.id} from paid commercial work`,
      entityType: 'order',
      entityId: created.id,
    })
  }
  return getFulfillmentWorkspace()
}

export function createMockOrder(input: CreateServiceOrderInput): FulfillmentWorkspace {
  const stamp = Date.now().toString().slice(-8)
  const id = `ORD-${stamp}`
  const workflowStages =
    input.workflowStages.length > 0
      ? input.workflowStages.slice(0, 6)
      : ['Order Setup', 'Execution', 'Review', 'Handover']

  orders.unshift({
    id,
    requestId: input.requestId ?? 'Manual',
    ...(input.quotationId ? { quotationId: input.quotationId } : {}),
    ...(input.invoiceId ? { invoiceId: input.invoiceId } : {}),
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
        'Commercial Operations',
        input.paymentReady
          ? 'Commercial and payment eligibility confirmed.'
          : 'Order created pending mobilisation.',
      ),
    ],
  })

  appendMockAuditEvent({
    area: 'Order',
    action: `Created ${id} for ${input.client}`,
    entityType: 'order',
    entityId: id,
  })
  return getFulfillmentWorkspace()
}

export function updateMockOrder(
  orderId: string,
  input: UpdateServiceOrderInput,
): FulfillmentWorkspace {
  const order = orders.find((item) => item.id === orderId)
  if (!order) return getFulfillmentWorkspace()

  order.status = input.status
  order.progress = clampProgress(input.progress)
  order.stage = input.stage
  order.nextAction = input.nextAction
  order.activities.push(
    activity(
      `${order.id}-A${order.activities.length + 1}`,
      nowIso(),
      'Order control update',
      'Service Manager',
      `${order.status}; ${order.progress}% complete; next: ${order.nextAction}`,
    ),
  )

  appendMockAuditEvent({
    area: 'Order',
    action: `Updated ${orderId}`,
    entityType: 'order',
    entityId: orderId,
  })
  return getFulfillmentWorkspace()
}

export function advanceMockOrder(orderId: string): FulfillmentWorkspace {
  const order = orders.find((item) => item.id === orderId)
  if (!order) return getFulfillmentWorkspace()

  const result = advanceMilestones(order.milestones)
  if (result.completed && !canCompleteOrderWithDeliverables(deliverables, order.id)) {
    order.activities.push(
      activity(
        `${order.id}-A${order.activities.length + 1}`,
        nowIso(),
        'Completion blocked',
        'System',
        'Required deliverables must be approved before order completion.',
      ),
    )
    return getFulfillmentWorkspace()
  }
  order.milestones = result.milestones
  order.progress = result.progress
  order.stage = result.stage
  order.status = result.completed ? 'Completed' : 'Active'
  order.nextAction = result.completed ? 'Collect feedback' : `Complete ${result.stage}`
  order.activities.push(
    activity(
      `${order.id}-A${order.activities.length + 1}`,
      nowIso(),
      'Stage advanced',
      'Service Manager',
      `Moved to ${order.stage}.`,
    ),
  )

  appendMockAuditEvent({
    area: 'Order',
    action: `Advanced ${orderId} to ${order.stage}`,
    entityType: 'order',
    entityId: orderId,
  })
  return getFulfillmentWorkspace()
}

export function addMockOrderUpdate(input: AddOrderUpdateInput): FulfillmentWorkspace {
  const order = orders.find((item) => item.id === input.orderId)
  if (!order) return getFulfillmentWorkspace()

  order.progress = clampProgress(input.progress)
  if (input.nextAction.trim()) order.nextAction = input.nextAction.trim()
  order.activities.push({
    id: `${order.id}-A${order.activities.length + 1}`,
    at: nowIso(),
    title: input.type,
    actor: 'Service Manager',
    description: input.note,
    visibility: input.visibility,
  })

  appendMockAuditEvent({
    area: 'Order',
    action: `Recorded progress update for ${order.id}`,
    entityType: 'order',
    entityId: order.id,
  })
  return getFulfillmentWorkspace()
}

export function addMockMilestone(input: AddMilestoneInput): FulfillmentWorkspace {
  const order = orders.find((item) => item.id === input.orderId)
  if (!order || !input.name.trim()) return getFulfillmentWorkspace()

  order.milestones.push({
    id: `${order.id}-M${order.milestones.length + 1}`,
    name: input.name.trim(),
    status: 'Pending',
  })
  appendMockAuditEvent({
    area: 'Milestone',
    action: `Added milestone "${input.name.trim()}" to ${order.id}`,
    entityType: 'order',
    entityId: order.id,
  })
  return getFulfillmentWorkspace()
}

export function createMockTask(input: CreateExecutionTaskInput): FulfillmentWorkspace {
  const id = `TSK-${Date.now().toString().slice(-5)}`
  const order = orders.find((item) => item.id === input.orderId)

  tasks.unshift({
    id,
    title: input.title,
    orderId: input.orderId,
    stageName: order?.stage ?? 'Unassigned stage',
    status: 'To Do',
    owner: input.owner,
    dueAt: input.dueAt,
    priority: input.priority,
    evidenceRequired: input.evidenceRequired,
    instructions: input.instructions,
    progress: 0,
    evidence: [],
    activities: [
      {
        id: `${id}-A1`,
        at: nowIso(),
        title: 'Task created',
        actor: 'Service Manager',
        description: input.instructions || 'Execution task created.',
      },
    ],
  })
  if (order) {
    order.activities.push(
      activity(
        `${order.id}-A${order.activities.length + 1}`,
        nowIso(),
        'Execution task created',
        'Service Manager',
        `${id}: ${input.title}`,
      ),
    )
  }

  appendMockAuditEvent({
    area: 'Task',
    action: `Created ${id} for ${input.orderId}`,
    entityType: 'task',
    entityId: id,
  })
  return getFulfillmentWorkspace()
}

export function updateMockTask(
  taskId: string,
  input: UpdateExecutionTaskInput,
): FulfillmentWorkspace {
  const task = tasks.find((item) => item.id === taskId)
  if (!task) return getFulfillmentWorkspace()

  const addActivity = (title: string, description: string) => {
    task.activities.push({
      id: `${task.id}-A${task.activities.length + 1}`,
      at: nowIso(),
      title,
      actor: 'Service Manager',
      description,
    })
  }

  if (input.action === 'advance') {
    const next = nextTaskStatus(task.status)
    task.status = next
    task.progress = taskProgressForStatus(next, task.progress)
    addActivity('Task advanced', `Task moved to ${next}.`)
  }

  if (input.action === 'save') {
    if (input.progress !== undefined) task.progress = clampProgress(input.progress)
    if (input.owner !== undefined) task.owner = input.owner
    if (input.dueAt !== undefined) task.dueAt = input.dueAt
    if (input.priority !== undefined) task.priority = input.priority
    addActivity('Task updated', input.note || 'Task controls updated.')
  }

  if (input.action === 'block') {
    task.status = 'Blocked'
    task.blockedReason = input.blockedReason?.trim() || 'Blocked pending resolution.'
    addActivity('Task blocked', task.blockedReason)
  }

  if (input.action === 'unblock') {
    task.status = 'In Progress'
    delete task.blockedReason
    task.progress = taskProgressForStatus('In Progress', task.progress)
    addActivity('Task unblocked', input.note || 'Blocker resolved.')
  }

  if (input.action === 'complete') {
    task.status = 'Done'
    task.progress = 100
    task.completedAt = nowIso()
    delete task.blockedReason
    addActivity('Task completed', input.note || 'Task completed.')
  }

  if (input.action === 'add-evidence' && input.evidence) {
    task.evidence.push({
      id: `${task.id}-E${task.evidence.length + 1}`,
      label: input.evidence.label,
      fileName: input.evidence.fileName,
      addedAt: nowIso(),
      addedBy: 'Service Manager',
    })
    addActivity('Evidence added', `${input.evidence.label}: ${input.evidence.fileName}`)
  }

  if (input.action === 'add-activity') {
    addActivity('Task activity', input.note || 'Task activity recorded.')
  }

  const order = orders.find((item) => item.id === task.orderId)
  if (order) {
    order.activities.push(
      activity(
        `${order.id}-A${order.activities.length + 1}`,
        nowIso(),
        'Execution task updated',
        task.owner,
        `${task.id}: ${task.status}; ${task.progress}% complete.`,
      ),
    )
  }

  appendMockAuditEvent({
    area: 'Task',
    action: `${taskId}: ${input.action}`,
    entityType: 'task',
    entityId: taskId,
  })
  return getFulfillmentWorkspace()
}

export function createMockDeliverable(input: CreateDeliverableInput): FulfillmentWorkspace {
  const order = orders.find((item) => item.id === input.orderId)
  const id = `DEL-${Date.now().toString().slice(-5)}`
  deliverables.unshift({
    id,
    orderId: input.orderId,
    title: input.title,
    type: input.type,
    version: input.version,
    owner: order?.owner ?? 'Service Manager',
    status: input.approvalMode === 'No approval' ? 'Approved' : 'Under Review',
    clientVisible: input.clientVisible,
    date: today(),
    approvalMode: input.approvalMode,
    fileName: input.fileName,
  })
  if (order)
    order.activities.push(
      activity(
        `${order.id}-A${order.activities.length + 1}`,
        nowIso(),
        'Deliverable added',
        order.owner,
        `${input.title} (${input.version}) added to the order.`,
      ),
    )
  appendMockAuditEvent({
    area: 'Deliverable',
    action: `Created ${id} for ${input.orderId}`,
    entityType: 'deliverable',
    entityId: id,
  })
  return getFulfillmentWorkspace()
}
export function decideMockDeliverable(
  deliverableId: string,
  input: DecideDeliverableInput,
): FulfillmentWorkspace {
  const item = deliverables.find((d) => d.id === deliverableId)
  if (!item) return getFulfillmentWorkspace()
  item.status = input.action === 'approve' ? 'Approved' : 'Rejected'
  appendMockAuditEvent({
    area: 'Deliverable',
    action: `${input.action === 'approve' ? 'Approved' : 'Rejected'} ${deliverableId}`,
    entityType: 'deliverable',
    entityId: deliverableId,
  })
  return getFulfillmentWorkspace()
}
