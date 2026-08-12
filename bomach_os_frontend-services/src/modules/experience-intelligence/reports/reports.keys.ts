export const reportsKeys = {
  all: ['reports'] as const,
  kpis: () => [...reportsKeys.all, 'kpis'] as const,
  servicePerformance: () => [...reportsKeys.all, 'service-performance'] as const,
  branchPerformance: () => [...reportsKeys.all, 'branch-performance'] as const,
}
