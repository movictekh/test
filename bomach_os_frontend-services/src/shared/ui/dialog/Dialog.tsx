import { IconX } from '@tabler/icons-react'
import { useEffect, useId, useRef, type MouseEvent as ReactMouseEvent, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/button'

export type DialogSize = 'sm' | 'md' | 'lg' | 'xl'

const sizeClasses: Record<DialogSize, string> = {
  sm: 'max-w-md',
  md: 'max-w-xl',
  lg: 'max-w-3xl',
  xl: 'max-w-5xl',
}

export interface DialogProps {
  open: boolean
  title: ReactNode
  description?: ReactNode
  children: ReactNode
  footer?: ReactNode
  size?: DialogSize
  closeOnBackdrop?: boolean
  closeOnEscape?: boolean
  preventClose?: boolean
  onClose: () => void
}

export function Dialog({
  open,
  title,
  description,
  children,
  footer,
  size = 'md',
  closeOnBackdrop = true,
  closeOnEscape = true,
  preventClose = false,
  onClose,
}: DialogProps) {
  const titleId = useId()
  const descriptionId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) return

    previousFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    window.requestAnimationFrame(() => closeButtonRef.current?.focus())

    return () => {
      document.body.style.overflow = previousOverflow
      previousFocusRef.current?.focus()
    }
  }, [open])

  useEffect(() => {
    if (!open) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && closeOnEscape && !preventClose) {
        event.preventDefault()
        onClose()
        return
      }

      if (event.key !== 'Tab' || !dialogRef.current) return

      const elements = dialogRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )

      if (elements.length === 0) {
        event.preventDefault()
        return
      }

      const first = elements[0]
      const last = elements[elements.length - 1]

      if (!first || !last) return

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [closeOnEscape, onClose, open, preventClose])

  if (!open || typeof document === 'undefined') return null

  const handleBackdropClick = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget && closeOnBackdrop && !preventClose) {
      onClose()
    }
  }

  return createPortal(
    <div
      className="bg-overlay fixed inset-0 z-[110] grid place-items-center overflow-y-auto p-4"
      onMouseDown={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        className={cn(
          'border-border bg-surface shadow-overlay flex max-h-[calc(100vh-2rem)] w-full flex-col rounded-2xl border',
          sizeClasses[size],
        )}
      >
        <header className="border-border flex items-start justify-between gap-4 border-b p-5 sm:p-6">
          <div className="min-w-0">
            <h2 id={titleId} className="text-foreground text-lg font-black">
              {title}
            </h2>
            {description ? (
              <p id={descriptionId} className="text-foreground-muted mt-1 text-sm leading-6">
                {description}
              </p>
            ) : null}
          </div>

          <Button
            ref={closeButtonRef}
            variant="ghost"
            size="icon"
            className="-mt-2 -mr-2 size-9 shrink-0"
            aria-label="Close dialog"
            disabled={preventClose}
            onClick={onClose}
          >
            <IconX size={18} />
          </Button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-5 sm:p-6">{children}</div>

        {footer ? (
          <footer className="border-border bg-surface-muted flex flex-wrap justify-end gap-2 rounded-b-2xl border-t px-5 py-4 sm:px-6">
            {footer}
          </footer>
        ) : null}
      </div>
    </div>,
    document.body,
  )
}
