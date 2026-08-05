import {
  IconBell,
  IconBuildingCommunity,
  IconChevronLeft,
  IconChevronRight,
  IconLayoutDashboard,
  IconMenu2,
  IconSearch,
  IconSettings,
  IconX,
} from '@tabler/icons-react'
import { useState, type PropsWithChildren } from 'react'

import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/button'

const navigation = [
  {
    label: 'Foundation',
    icon: IconLayoutDashboard,
    active: true,
  },
  {
    label: 'Service Administration',
    icon: IconSettings,
    active: false,
  },
  {
    label: 'Commercial Operations',
    icon: IconBuildingCommunity,
    active: false,
  },
] as const

export function AppShell({ children }: PropsWithChildren) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="bg-background min-h-screen">
      <header className="bg-brand-600 fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between px-4 text-white shadow-sm lg:px-5">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/10 hover:text-white lg:hidden"
            aria-label="Open navigation"
            onClick={() => setMobileSidebarOpen(true)}
          >
            <IconMenu2 size={20} />
          </Button>

          <div className="bg-accent-600 grid size-10 place-items-center rounded-xl text-lg font-black">
            B
          </div>

          <div>
            <p className="text-sm font-bold">Bomach Group</p>
            <p className="text-[0.6875rem] text-white/60">Service Operations OS</p>
          </div>
        </div>

        <div className="hidden w-full max-w-sm items-center gap-2 rounded-full bg-white/10 px-4 py-2 md:flex">
          <IconSearch size={16} className="text-white/60" aria-hidden="true" />
          <input
            type="search"
            aria-label="Global search"
            placeholder="Search requests, clients, and orders"
            className="w-full border-0 bg-transparent text-xs text-white outline-none placeholder:text-white/50"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="hidden rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold sm:inline-flex">
            Service Administrator
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/10 hover:text-white"
            aria-label="Notifications"
          >
            <IconBell size={19} />
          </Button>
          <span className="grid size-9 place-items-center rounded-full bg-white/15 text-xs font-bold">
            KE
          </span>
        </div>
      </header>

      {mobileSidebarOpen ? (
        <button
          type="button"
          aria-label="Close navigation"
          className="bg-overlay fixed inset-0 z-40 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      ) : null}

      <aside
        className={cn(
          'border-border bg-surface fixed top-16 bottom-0 left-0 z-50 flex flex-col border-r transition-[width,transform] duration-200 lg:z-30 lg:translate-x-0',
          sidebarCollapsed ? 'w-20' : 'w-60',
          mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="border-border flex items-center justify-end border-b p-3 lg:hidden">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Close navigation"
            onClick={() => setMobileSidebarOpen(false)}
          >
            <IconX size={18} />
          </Button>
        </div>

        <nav
          aria-label="Main navigation"
          className="flex-1 scrollbar-thin space-y-1 overflow-y-auto p-3"
        >
          {navigation.map((item) => {
            const Icon = item.icon

            return (
              <button
                key={item.label}
                type="button"
                disabled={!item.active}
                className={cn(
                  'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs font-semibold transition-colors',
                  item.active
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-foreground-muted hover:bg-surface-muted',
                  !item.active && 'cursor-not-allowed opacity-45',
                  sidebarCollapsed && 'justify-center px-2',
                )}
                title={sidebarCollapsed ? item.label : undefined}
              >
                <Icon size={18} aria-hidden="true" />
                {sidebarCollapsed ? null : <span>{item.label}</span>}
              </button>
            )
          })}
        </nav>

        <div className="border-border hidden border-t p-3 lg:block">
          <Button
            variant="ghost"
            size="sm"
            fullWidth
            aria-label={sidebarCollapsed ? 'Expand navigation' : 'Collapse navigation'}
            onClick={() => setSidebarCollapsed((current) => !current)}
          >
            {sidebarCollapsed ? <IconChevronRight size={17} /> : <IconChevronLeft size={17} />}
            {sidebarCollapsed ? null : 'Collapse'}
          </Button>
        </div>
      </aside>

      <div
        className={cn(
          'min-h-screen pt-16 transition-[padding] duration-200',
          sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-60',
        )}
      >
        {children}
      </div>
    </div>
  )
}
