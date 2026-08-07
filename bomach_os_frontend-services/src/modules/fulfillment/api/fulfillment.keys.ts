export const fulfillmentKeys = {
  all: ['fulfillment'] as const,
  workspace: () => [...fulfillmentKeys.all, 'workspace'] as const,
}
