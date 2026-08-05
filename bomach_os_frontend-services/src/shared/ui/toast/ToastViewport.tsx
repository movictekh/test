import { createPortal } from 'react-dom'

import { Toast } from './Toast'
import type { ToastRecord } from './toast.types'

interface ToastViewportProps {
  toasts: readonly ToastRecord[]
  onDismiss: (id: string) => void
}

export function ToastViewport({ toasts, onDismiss }: ToastViewportProps) {
  if (typeof document === 'undefined') {
    return null
  }

  return createPortal(
    <div
      aria-label="Application notifications"
      className="pointer-events-none fixed right-4 bottom-4 z-[100] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-3 sm:right-5 sm:bottom-5"
    >
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>,
    document.body,
  )
}
