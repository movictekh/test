export const dashboardKeys = {
  all: ['dashboard'] as const,
  summary: (userId: string) => [...dashboardKeys.all, 'summary', userId] as const,
  recentActivity: () => [...dashboardKeys.all, 'recent-activity'] as const,
}
