import type { ReactNode } from 'react'

export const TOAST_TONES = ['info', 'success', 'warning', 'danger'] as const

export type ToastTone = (typeof TOAST_TONES)[number]

export interface ToastAction {
  label: string
  onClick: () => void
}

export interface ToastInput {
  title: ReactNode
  description?: ReactNode
  tone?: ToastTone
  duration?: number
  action?: ToastAction
}

export interface ToastRecord extends ToastInput {
  id: string
  tone: ToastTone
  duration: number
}

export interface ToastContextValue {
  toasts: readonly ToastRecord[]
  showToast: (input: ToastInput) => string
  dismissToast: (id: string) => void
  dismissAllToasts: () => void
  success: (title: ReactNode, options?: Omit<ToastInput, 'title' | 'tone'>) => string
  error: (title: ReactNode, options?: Omit<ToastInput, 'title' | 'tone'>) => string
  warning: (title: ReactNode, options?: Omit<ToastInput, 'title' | 'tone'>) => string
  info: (title: ReactNode, options?: Omit<ToastInput, 'title' | 'tone'>) => string
}
