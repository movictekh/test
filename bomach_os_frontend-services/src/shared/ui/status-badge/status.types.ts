export const STATUS_TONES = ['neutral', 'info', 'success', 'warning', 'danger', 'purple'] as const

export type StatusTone = (typeof STATUS_TONES)[number]

export interface StatusDefinition {
  label: string
  tone: StatusTone
  description?: string
}
