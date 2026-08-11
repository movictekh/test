import { IconX } from '@tabler/icons-react'
import type { FormEvent, ReactNode } from 'react'

type TaskModalShellProps = {
  as?: 'form' | 'section'
  ariaLabel: string
  className?: string
  bodyClassName?: string
  title: ReactNode
  subtitle?: ReactNode
  headerMeta?: ReactNode
  footer?: ReactNode
  onClose: () => void
  onSubmit?: (event: FormEvent<HTMLFormElement>) => void
  children: ReactNode
}

export function TaskModalShell({
  as = 'section',
  ariaLabel,
  className,
  bodyClassName,
  title,
  subtitle,
  headerMeta,
  footer,
  onClose,
  onSubmit,
  children,
}: TaskModalShellProps) {
  const Component = as
  const isForm = as === 'form'

  return (
    <div className="commercial-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <Component
        className={`commercial-modal commercial-modal--xl fulfillment-task-modal ${
          className ?? ''
        }`.trim()}
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        onMouseDown={(event) => event.stopPropagation()}
        {...(isForm && onSubmit ? { onSubmit } : {})}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>{title}</h2>
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
          <div className="commercial-modal-header-meta">
            {headerMeta}
            <button
              type="button"
              className="commercial-modal-close"
              onClick={onClose}
              aria-label="Close"
            >
              <IconX size={16} />
            </button>
          </div>
        </header>

        <div className={`commercial-modal-body fulfillment-task-modal-body ${bodyClassName ?? ''}`.trim()}>
          {children}
        </div>

        {footer ? <footer className="commercial-modal-footer">{footer}</footer> : null}
      </Component>
    </div>
  )
}
