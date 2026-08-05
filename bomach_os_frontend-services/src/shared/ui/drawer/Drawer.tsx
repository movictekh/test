import { IconX } from '@tabler/icons-react'
import { useEffect, useId, useRef, type MouseEvent as ReactMouseEvent, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/button'

export type DrawerSide = 'left' | 'right' | 'bottom'
export type DrawerSize = 'sm' | 'md' | 'lg'

const sizeClasses: Record<DrawerSide, Record<DrawerSize, string>> = {
  left: { sm: 'w-80', md: 'w-96', lg: 'w-[32rem]' },
  right: { sm: 'w-80', md: 'w-96', lg: 'w-[32rem]' },
  bottom: { sm: 'max-h-[40vh]', md: 'max-h-[65vh]', lg: 'max-h-[85vh]' },
}

export interface DrawerProps {
  open: boolean
  title: ReactNode
  description?: ReactNode
  children: ReactNode
  footer?: ReactNode
  side?: DrawerSide
  size?: DrawerSize
  onClose: () => void
}

export function Drawer({
  open,
  title,
  description,
  children,
  footer,
  side = 'right',
  size = 'md',
  onClose,
}: DrawerProps) {
  const titleId = useId()
  const descriptionId = useId()
  const drawerRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) return

    previousFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.requestAnimationFrame(() => closeButtonRef.current?.focus())

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }

      if (event.key !== 'Tab' || !drawerRef.current) return

      const elements = drawerRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )

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

    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', handleKeyDown)
      previousFocusRef.current?.focus()
    }
  }, [onClose, open])

  if (!open || typeof document === 'undefined') return null

  const positionClasses =
    side === 'left'
      ? 'inset-y-0 left-0 h-full'
      : side === 'right'
        ? 'inset-y-0 right-0 h-full'
        : 'inset-x-0 bottom-0 w-full rounded-t-2xl'

  const handleBackdropClick = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) onClose()
  }

  return createPortal(
    <div className="bg-overlay fixed inset-0 z-[110]" onMouseDown={handleBackdropClick}>
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        className={cn(
          'border-border bg-surface shadow-overlay absolute flex max-w-[calc(100vw-1rem)] flex-col border',
          positionClasses,
          sizeClasses[side][size],
          side === 'left' && 'border-r',
          side === 'right' && 'border-l',
          side === 'bottom' && 'border-t',
        )}
      >
        <header className="border-border flex items-start justify-between gap-4 border-b p-4 sm:p-5">
          <div className="min-w-0">
            <h2 id={titleId} className="text-foreground text-base font-black">
              {title}
            </h2>
            {description ? (
              <p id={descriptionId} className="text-foreground-muted mt-1 text-xs leading-5">
                {description}
              </p>
            ) : null}
          </div>
          <Button
            ref={closeButtonRef}
            variant="ghost"
            size="icon"
            className="-mt-1 -mr-1 size-9 shrink-0"
            aria-label="Close drawer"
            onClick={onClose}
          >
            <IconX size={18} />
          </Button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-5">{children}</div>

        {footer ? (
          <footer className="border-border bg-surface-muted flex flex-wrap justify-end gap-2 border-t p-4 sm:p-5">
            {footer}
          </footer>
        ) : null}
      </div>
    </div>,
    document.body,
  )
}
