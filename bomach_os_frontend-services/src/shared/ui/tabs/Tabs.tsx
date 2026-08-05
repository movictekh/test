import {
  createContext,
  useContext,
  useId,
  useMemo,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type KeyboardEvent,
  type PropsWithChildren,
} from 'react'

import { cn } from '@/shared/lib/cn'

interface TabsContextValue {
  value: string
  setValue: (value: string) => void
  idPrefix: string
}

const TabsContext = createContext<TabsContextValue | undefined>(undefined)

function useTabsContext() {
  const context = useContext(TabsContext)
  if (!context) throw new Error('Tabs components must be used inside Tabs.')
  return context
}

export interface TabsProps extends PropsWithChildren {
  value?: string
  defaultValue?: string
  onValueChange?: (value: string) => void
  className?: string
}

export function Tabs({ value, defaultValue = '', onValueChange, children, className }: TabsProps) {
  const [internalValue, setInternalValue] = useState(defaultValue)
  const idPrefix = useId()
  const resolvedValue = value ?? internalValue

  const context = useMemo<TabsContextValue>(
    () => ({
      value: resolvedValue,
      idPrefix,
      setValue: (nextValue) => {
        if (value === undefined) setInternalValue(nextValue)
        onValueChange?.(nextValue)
      },
    }),
    [idPrefix, onValueChange, resolvedValue, value],
  )

  return (
    <TabsContext.Provider value={context}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  )
}

export function TabsList({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return

    const tabs = Array.from(
      event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]:not([disabled])'),
    )

    const currentIndex = tabs.indexOf(document.activeElement as HTMLButtonElement)
    if (currentIndex < 0 || tabs.length === 0) return

    event.preventDefault()

    let nextIndex = currentIndex
    if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length
    if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = tabs.length - 1

    tabs[nextIndex]?.focus()
    tabs[nextIndex]?.click()
  }

  return (
    <div
      role="tablist"
      className={cn('border-border flex gap-1 overflow-x-auto border-b', className)}
      onKeyDown={handleKeyDown}
      {...props}
    />
  )
}

export interface TabsTriggerProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'value'> {
  value: string
}

export function TabsTrigger({ value, className, children, ...props }: TabsTriggerProps) {
  const context = useTabsContext()
  const selected = context.value === value

  return (
    <button
      type="button"
      role="tab"
      id={`${context.idPrefix}-tab-${value}`}
      aria-selected={selected}
      aria-controls={`${context.idPrefix}-panel-${value}`}
      tabIndex={selected ? 0 : -1}
      className={cn(
        'border-b-2 px-3 py-3 text-xs font-bold whitespace-nowrap transition-colors',
        selected
          ? 'border-brand-600 text-brand-700'
          : 'text-foreground-muted hover:text-foreground border-transparent',
        className,
      )}
      onClick={() => context.setValue(value)}
      {...props}
    >
      {children}
    </button>
  )
}

export interface TabsContentProps extends HTMLAttributes<HTMLDivElement> {
  value: string
}

export function TabsContent({ value, className, children, ...props }: TabsContentProps) {
  const context = useTabsContext()
  const selected = context.value === value

  if (!selected) return null

  return (
    <div
      role="tabpanel"
      id={`${context.idPrefix}-panel-${value}`}
      aria-labelledby={`${context.idPrefix}-tab-${value}`}
      tabIndex={0}
      className={cn('pt-4 outline-none', className)}
      {...props}
    >
      {children}
    </div>
  )
}
