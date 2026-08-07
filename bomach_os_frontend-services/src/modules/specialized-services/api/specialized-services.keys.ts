export const specializedServicesKeys = {
  all: ['specialized-services'] as const,
  workspace: () => ['specialized-services', 'workspace'] as const,
}
