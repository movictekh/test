export const serviceAdministrationKeys = {
  all: ['service-administration'] as const,
  workspace: () => [...serviceAdministrationKeys.all, 'workspace'] as const,
}
