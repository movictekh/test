import {
  useCallback,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
  type ReactNode,
} from 'react'

import { ToastContext } from './toast.context'
import { ToastViewport } from './ToastViewport'
import type { ToastContextValue, ToastInput, ToastRecord, ToastTone } from './toast.types'

const DEFAULT_DURATION = 5_000
const MAX_VISIBLE_TOASTS = 4

function createToastId(counter: number): string {
  return `toast-${Date.now()}-${counter}`
}

export function ToastProvider({ children }: PropsWithChildren) {
  const [toasts, setToasts] = useState<ToastRecord[]>([])
  const counterRef = useRef(0)

  const dismissToast = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const dismissAllToasts = useCallback(() => {
    setToasts([])
  }, [])

  const showToast = useCallback((input: ToastInput): string => {
    counterRef.current += 1
    const id = createToastId(counterRef.current)
    const tone = input.tone ?? 'info'
    const nextToast: ToastRecord = {
      ...input,
      id,
      tone,
      duration: input.duration ?? DEFAULT_DURATION,
    }

    setToasts((current) => {
      // A new error/warning replaces prior ones of the same tone so they don't stack.
      const remaining =
        tone === 'danger' || tone === 'warning'
          ? current.filter((toast) => toast.tone !== tone)
          : current
      return [...remaining, nextToast].slice(-MAX_VISIBLE_TOASTS)
    })

    return id
  }, [])

  const createToneHelper = useCallback(
    (tone: ToastTone, title: ReactNode, options?: Omit<ToastInput, 'title' | 'tone'>) =>
      showToast({
        ...options,
        title,
        tone,
      }),
    [showToast],
  )

  const value = useMemo<ToastContextValue>(
    () => ({
      toasts,
      showToast,
      dismissToast,
      dismissAllToasts,
      success: (title, options) => createToneHelper('success', title, options),
      error: (title, options) => createToneHelper('danger', title, options),
      warning: (title, options) => createToneHelper('warning', title, options),
      info: (title, options) => createToneHelper('info', title, options),
    }),
    [createToneHelper, dismissAllToasts, dismissToast, showToast, toasts],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  )
}
