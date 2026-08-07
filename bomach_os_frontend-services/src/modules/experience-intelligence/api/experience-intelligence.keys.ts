export const experienceIntelligenceKeys = {
  all: ['experience-intelligence'] as const,
  workspace: () => [...experienceIntelligenceKeys.all, 'workspace'] as const,
}
