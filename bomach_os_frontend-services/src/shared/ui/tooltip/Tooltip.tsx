import {
  cloneElement,
  isValidElement,
  useId,
  useState,
  type ReactElement,
  type ReactNode,
} from 'react'

import { cn } from '@/shared/lib/cn'

export interface TooltipProps {
  content: ReactNode
  children: ReactElement
  side?: 'top' | 'right' | 'bottom' | 'left'
  className?: string
}

const positionClasses = {
  top: 'bottom-full left-1/2 mb-2 -translate-x-1/2',
  right: 'top-1/2 left-full ml-2 -translate-y-1/2',
  bottom: 'top-full left-1/2 mt-2 -translate-x-1/2',
  left: 'top-1/2 right-full mr-2 -translate-y-1/2',
} as const

export function Tooltip({ content, children, side = 'top', className }: TooltipProps) {
  const [visible, setVisible] = useState(false)
  const tooltipId = useId()

  if (!isValidElement(children)) return children

  const child = cloneElement(children, {
    'aria-describedby': visible ? tooltipId : undefined,
    onMouseEnter: () => setVisible(true),
    onMouseLeave: () => setVisible(false),
    onFocus: () => setVisible(true),
    onBlur: () => setVisible(false),
  } as Record<string, unknown>)

  return (
    <span className="relative inline-flex">
      {child}
      {visible ? (
        <span
          id={tooltipId}
          role="tooltip"
          className={cn(
            'bg-foreground shadow-overlay absolute z-50 max-w-64 rounded-md px-2.5 py-1.5 text-[0.6875rem] leading-4 font-semibold text-white',
            positionClasses[side],
            className,
          )}
        >
          {content}
        </span>
      ) : null}
    </span>
  )
}
