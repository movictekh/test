import {
  IconBook,
  IconBuildingCommunity,
  IconCalculator,
  IconClipboardCheck,
  IconCreditCard,
  IconChevronLeft,
  IconChevronRight,
  IconFileInvoice,
  IconForms,
  IconGitBranch,
  IconHistory,
  IconLayoutDashboard,
  IconLogout,
  IconMenu2,
  IconMessageStar,
  IconPackage,
  IconReceipt,
  IconChartBar,
  IconSettings,
  IconShieldCheck,
  IconListCheck,
  IconFolders,
  IconX,
} from '@tabler/icons-react'
import { Link, useNavigate, useRouter, useRouterState } from '@tanstack/react-router'
import { useMemo, useState, type PropsWithChildren } from 'react'

import { formatRoleLabel, useAuth } from '@/app/auth'
import { NotificationPanel } from '@/app/notifications'
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
  quotations: IconFileInvoice,
  invoices: IconReceipt,
  approvals: IconShieldCheck,
  orders: IconPackage,
  tasks: IconListCheck,
  deliverables: IconFolders,
  feedback: IconMessageStar,
  reports: IconChartBar,
  audit: IconHistory,
  payments: IconCreditCard,
  documents: IconClipboardCheck,
}

interface AppShellProps extends PropsWithChildren {
  navigation: readonly NavigationGroup[]
}

export function AppShell({ children, navigation }: AppShellProps) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem('bomach.operations.sidebar-collapsed') === 'true'
  })
  const { user, signOut } = useAuth()
  const router = useRouter()
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (state) => state.location.pathname })

  const visibleNavigation = useMemo(
    () => getVisibleNavigation(navigation, user),
    [navigation, user],
  )

  const toggleSidebar = () => {
    setSidebarCollapsed((current) => {
      const next = !current
      window.localStorage.setItem('bomach.operations.sidebar-collapsed', String(next))
      return next
    })
  }

  const handleSignOut = async () => {
    await signOut()
    await router.invalidate()
    await navigate({ to: '/login', replace: true })
  }

  const productName = 'Service Operations OS'

  return (
    <div className="bg-background h-dvh overflow-hidden">
      <header className="bg-brand-600 fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between px-4 text-white shadow-sm lg:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 text-white hover:bg-white/10 hover:text-white lg:hidden"
            aria-label="Open navigation"
            aria-controls="operations-navigation"
            aria-expanded={mobileSidebarOpen}
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

        <div className="flex items-center gap-2">
          {user ? (
            <span className="hidden rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold xl:inline-flex">
              {formatRoleLabel(user.role)}
            </span>
          ) : null}

          <div className="hidden text-right sm:block">
            <p className="max-w-36 truncate text-xs font-semibold">{user?.name ?? 'Bomach User'}</p>
            <p className="max-w-36 truncate text-[0.625rem] text-white/60">
              {user?.email ?? 'No active session'}
            </p>
          </div>

          <span className="grid size-9 shrink-0 place-items-center rounded-full bg-white/15 text-xs font-bold">
            {user?.initials ?? 'BU'}
          </span>

          <NotificationPanel />
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
        id="operations-navigation"
        className={cn(
          'border-border bg-surface fixed top-16 bottom-0 left-0 z-50 flex flex-col border-r transition-[width,transform] duration-200 lg:z-30 lg:translate-x-0',
          sidebarCollapsed ? 'w-14' : 'w-60',
          mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="border-border flex items-center justify-between gap-1.5 border-b px-2 py-1.5">
          {sidebarCollapsed ? null : (
            <span className="text-foreground-muted hidden text-[0.5rem] leading-none font-bold tracking-[0.14em] uppercase lg:inline">
              Navigation
            </span>
          )}
          <span className="text-foreground-muted text-xs font-bold lg:hidden">Navigation</span>
          <Button
            variant="ghost"
            size="icon"
            aria-label={sidebarCollapsed ? 'Expand navigation' : 'Collapse navigation'}
            className="text-foreground-muted hover:bg-surface-muted hover:text-foreground hidden size-7 lg:inline-flex"
            onClick={toggleSidebar}
          >
            {sidebarCollapsed ? <IconChevronRight size={18} /> : <IconChevronLeft size={18} />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label="Close navigation"
            className="text-foreground-muted hover:bg-surface-muted hover:text-foreground size-7 lg:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          >
            <IconX size={18} />
          </Button>
        </div>

        <nav
          aria-label="Main navigation"
          className="flex-1 scrollbar-thin space-y-3 overflow-y-auto py-1.5"
        >
          {visibleNavigation.map((group) => (
            <section key={group.id} aria-labelledby={`${group.id}-navigation-label`}>
              {group.label && !sidebarCollapsed ? (
                <h2
                  id={`${group.id}-navigation-label`}
                  className="text-foreground-subtle mb-1 px-3 text-[0.5rem] font-extrabold tracking-[0.14em] uppercase"
                >
                  {group.label}
                </h2>
              ) : null}

              <div className="space-y-0.5 px-2">
                {group.items.map((item) => {
                  const Icon = navigationIcons[item.icon]
                  const active = isNavigationItemActive(pathname, item)
                  const itemClasses = cn(
                    'flex min-h-8 w-full items-center gap-2 rounded-md border-l-3 border-l-transparent px-2.5 py-1.5 text-left text-[0.65625rem] font-semibold transition-colors',
                    active
                      ? 'bg-brand-50 text-brand-700 border-l-brand-600'
                      : 'text-foreground-muted hover:bg-surface-muted hover:text-foreground',
                    sidebarCollapsed && 'justify-center px-1.5',
                  )

                  const content = (
                    <>
                      <Icon size={16} className="shrink-0" aria-hidden="true" />
                      {sidebarCollapsed ? null : (
                        <>
                          <span className="min-w-0 flex-1 truncate">{item.label}</span>
                          {item.badge !== undefined ? (
                            <span
                              className={cn(
                                'ml-auto rounded-full px-1.5 py-0.5 text-[0.5rem] font-extrabold',
                                item.badgeTone === 'alert'
                                  ? 'bg-danger-50 text-danger-700'
                                  : 'bg-brand-50 text-brand-700',
                              )}
                            >
                              {item.badge}
                            </span>
                          ) : null}
                        </>
                      )}
                    </>
                  )

                  return (
                    <Link
                      key={item.id}
                      to={item.to}
                      {...(item.params ? { params: item.params } : {})}
                      className={itemClasses}
                      aria-current={active ? 'page' : undefined}
                      title={sidebarCollapsed ? item.label : undefined}
                      onClick={() => setMobileSidebarOpen(false)}
                    >
                      {content}
                    </Link>
                  )
                })}
              </div>
            </section>
          ))}
        </nav>

        <div className="border-border space-y-2 border-t p-3">
          <Button
            variant="danger"
            size="sm"
            fullWidth
            className={cn('justify-start px-2.5', sidebarCollapsed && 'justify-center px-0')}
            onClick={handleSignOut}
          >
            <IconLogout size={16} />
            {sidebarCollapsed ? null : 'Sign out'}
          </Button>
        </div>
      </aside>

      <div
        className={cn(
          'flex h-dvh min-w-0 flex-col overflow-hidden pt-16 transition-[padding] duration-200',
          sidebarCollapsed ? 'lg:pl-14' : 'lg:pl-60',
        )}
      >
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">{children}</div>
      </div>
    </div>
  )
}
