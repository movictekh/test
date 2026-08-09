export const dashboardKeys = {
  all: ['command-center'] as const,
  financials: () => [...dashboardKeys.all, 'financials'] as const,
  pendingApprovals: () => [...dashboardKeys.all, 'pending-approvals'] as const,
  pipeline: () => [...dashboardKeys.all, 'pipeline'] as const,
  actionItems: () => [...dashboardKeys.all, 'action-items'] as const,
  activity: () => [...dashboardKeys.all, 'activity'] as const,
}
