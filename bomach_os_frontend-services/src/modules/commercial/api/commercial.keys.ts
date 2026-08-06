export const commercialKeys = {
  all: ['commercial'] as const,
  workspace: () => [...commercialKeys.all, 'workspace'] as const,
}
