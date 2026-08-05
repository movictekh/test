import {
  IconBell,
  IconBook,
  IconBuildingCommunity,
  IconCalculator,
  IconChecklist,
  IconChevronLeft,
  IconChevronRight,
  IconClipboardCheck,
  IconCreditCard,
  IconFileDescription,
  IconFileInvoice,
  IconForms,
  IconGitBranch,
  IconHistory,
  IconLayoutDashboard,
  IconLogout,
  IconMenu2,
  IconMessageCircle,
  IconReceipt,
  IconReportAnalytics,
  IconSearch,
  IconSettings,
  IconShieldCheck,
  IconStack2,
  IconUserCircle,
  IconX,
} from '@tabler/icons-react'
import { Link, useNavigate, useRouter, useRouterState } from '@tanstack/react-router'
import { useMemo, useState, type PropsWithChildren } from 'react'

import { formatRoleLabel, useAuth } from '@/app/auth'
import {
  getVisibleNavigation,
  isNavigationItemActive,
  type NavigationGroup,
  type NavigationIconName,
} from '@/app/navigation'
import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/button'

const navigationIcons: Record<NavigationIconName, typeof IconLayoutDashboard> = {
  dashboard: IconLayoutDashboard,
  services: IconSettings,
  calculator: IconCalculator,
  form: IconForms,
  workflow: IconGitBranch,
  branches: IconBuildingCommunity,
  requests: IconBook,
  quotations: IconReceipt,
  invoices: IconFileInvoice,
  approvals: IconShieldCheck,
  orders: IconStack2,
  tasks: IconChecklist,
  deliverables: IconFileDescription,
  feedback: IconMessageCircle,
  reports: IconReportAnalytics,
  audit: IconHistory,
  portal: IconUserCircle,
  payments: IconCreditCard,
  documents: IconClipboardCheck,
}

interface AppShellProps extends PropsWithChildren {
  navigation: readonly NavigationGroup[]
  variant?: 'operations' | 'portal'
}

export function AppShell({ children, navigation, variant = 'operations' }: AppShellProps) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const { user, signOut } = useAuth()
  const router = useRouter()
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (state) => state.location.pathname })

  const visibleNavigation = useMemo(
    () => getVisibleNavigation(navigation, user),
    [navigation, user],
  )

  const handleSignOut = async () => {
    await signOut()
    await router.invalidate()
    await navigate({ to: '/login', replace: true })
  }

  const productName = variant === 'portal' ? 'Client Service Portal' : 'Service Operations OS'
  const searchPlaceholder =
    variant === 'portal'
      ? 'Search your requests, orders, and documents'
      : 'Search requests, clients, and orders'

  return (
    <div className="bg-background min-h-screen">
      <header className="bg-brand-600 fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between px-4 text-white shadow-sm lg:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 text-white hover:bg-white/10 hover:text-white lg:hidden"
            aria-label="Open navigation"
            onClick={() => setMobileSidebarOpen(true)}
          >
            <IconMenu2 size={20} />
          </Button>

          <div className="bg-accent-600 grid size-10 shrink-0 place-items-center rounded-xl text-lg font-black">
            B
          </div>

          <div className="min-w-0">
            <p className="truncate text-sm font-bold">Bomach Group</p>
            <p className="truncate text-[0.6875rem] text-white/60">{productName}</p>
          </div>
        </div>

        <div className="hidden w-full max-w-sm items-center gap-2 rounded-full bg-white/10 px-4 py-2 md:flex">
          <IconSearch size={16} className="shrink-0 text-white/60" aria-hidden="true" />
          <input
            type="search"
            aria-label="Global search"
            placeholder={searchPlaceholder}
            className="w-full border-0 bg-transparent text-xs text-white outline-none placeholder:text-white/50"
          />
        </div>

        <div className="flex items-center gap-2">
          {user ? (
            <span className="hidden rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold xl:inline-flex">
              {formatRoleLabel(user.role)}
            </span>
          ) : null}

          <Button
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/10 hover:text-white"
            aria-label="Notifications"
          >
            <IconBell size={19} />
          </Button>

          <div className="hidden text-right sm:block">
            <p className="max-w-36 truncate text-xs font-semibold">{user?.name ?? 'Bomach User'}</p>
            <p className="max-w-36 truncate text-[0.625rem] text-white/60">
              {user?.email ?? 'No active session'}
            </p>
          </div>

          <span className="grid size-9 shrink-0 place-items-center rounded-full bg-white/15 text-xs font-bold">
            {user?.initials ?? 'BU'}
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
          sidebarCollapsed ? 'w-20' : 'w-64',
          mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="border-border flex items-center justify-between border-b p-3 lg:hidden">
          <span className="text-foreground-muted text-xs font-bold">Navigation</span>
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
          className="flex-1 scrollbar-thin space-y-5 overflow-y-auto p-3"
        >
          {visibleNavigation.map((group) => (
            <section key={group.id} aria-labelledby={`${group.id}-navigation-label`}>
              {group.label && !sidebarCollapsed ? (
                <h2
                  id={`${group.id}-navigation-label`}
                  className="text-foreground-subtle mb-1.5 px-3 text-[0.625rem] font-extrabold tracking-[0.12em] uppercase"
                >
                  {group.label}
                </h2>
              ) : null}

              <div className="space-y-1">
                {group.items.map((item) => {
                  const Icon = navigationIcons[item.icon]
                  const active = isNavigationItemActive(pathname, item)
                  const itemClasses = cn(
                    'flex min-h-10 w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs font-semibold transition-colors',
                    active
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-foreground-muted hover:bg-surface-muted hover:text-foreground',
                    sidebarCollapsed && 'justify-center px-2',
                    item.disabled && 'cursor-not-allowed opacity-45',
                  )

                  const content = (
                    <>
                      <Icon size={18} className="shrink-0" aria-hidden="true" />
                      {sidebarCollapsed ? null : (
                        <>
                          <span className="min-w-0 flex-1 truncate">{item.label}</span>
                          {item.disabled ? (
                            <span className="bg-surface-subtle text-foreground-subtle rounded px-1.5 py-0.5 text-[0.5625rem] font-bold uppercase">
                              Soon
                            </span>
                          ) : item.badge ? (
                            <span className="bg-accent-600 rounded-full px-1.5 py-0.5 text-[0.625rem] font-bold text-white">
                              {item.badge}
                            </span>
                          ) : null}
                        </>
                      )}
                    </>
                  )

                  if (item.to && !item.disabled) {
                    return (
                      <Link
                        key={item.id}
                        to={item.to}
                        className={itemClasses}
                        aria-current={active ? 'page' : undefined}
                        title={sidebarCollapsed ? item.label : undefined}
                        onClick={() => setMobileSidebarOpen(false)}
                      >
                        {content}
                      </Link>
                    )
                  }

                  return (
                    <button
                      key={item.id}
                      type="button"
                      disabled
                      className={itemClasses}
                      title={sidebarCollapsed ? `${item.label} — coming soon` : undefined}
                    >
                      {content}
                    </button>
                  )
                })}
              </div>
            </section>
          ))}
        </nav>

        <div className="border-border space-y-2 border-t p-3">
          <Button
            variant="ghost"
            size="sm"
            fullWidth
            className={cn(sidebarCollapsed && 'px-0')}
            onClick={handleSignOut}
          >
            <IconLogout size={17} />
            {sidebarCollapsed ? null : 'Sign out'}
          </Button>

          <Button
            variant="ghost"
            size="sm"
            fullWidth
            className={cn('hidden lg:inline-flex', sidebarCollapsed && 'px-0')}
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
          sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-64',
        )}
      >
        {children}
      </div>
    </div>
  )
}
