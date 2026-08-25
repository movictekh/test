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
  IconMessageStar,
  IconPackage,
  IconReceipt,
  IconChartBar,
  IconSettings,
  IconShieldCheck,
  IconListCheck,
  IconFolders,
} from '@tabler/icons-react'
import { Link, useNavigate, useRouter, useRouterState } from '@tanstack/react-router'
import { useMemo, useState, type PropsWithChildren } from 'react'

import { useAuth } from '@/app/auth'
import {
  getVisibleNavigation,
  isNavigationItemActive,
  type NavigationGroup,
  type NavigationIconName,
} from '@/app/navigation'
import { cn } from '@/shared/lib/cn'
import { ConfirmDialog } from '@/shared/ui'
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
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false)
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

  const searchParams = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '')
  const isEmbed = searchParams.get('embed') === 'true' || searchParams.get('embedded') === 'true'
  const hideSidebar = isEmbed || searchParams.get('hideSidebar') === 'true' || searchParams.get('hide_sidebar') === 'true'
  const compactSidebar = sidebarCollapsed && !mobileSidebarOpen

  return (
    <div className="bg-background h-dvh overflow-hidden">
      {mobileSidebarOpen && !hideSidebar ? (
        <button
          type="button"
          aria-label="Close navigation"
          className="bg-overlay fixed inset-0 z-40 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      ) : null}

      {!hideSidebar && (
        <aside
          id="operations-navigation"
          className={cn(
            'border-border bg-surface fixed top-0 bottom-0 left-0 z-50 flex flex-col border-r transition-[width,transform] duration-200 lg:z-30 lg:translate-x-0',
            compactSidebar ? 'w-14' : 'w-60',
            mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <div className="border-border hidden items-center justify-between gap-1.5 border-b px-2 py-1.5 lg:flex">
            {compactSidebar ? null : (
              <span className="text-foreground-muted text-[0.5rem] leading-none font-bold tracking-[0.14em] uppercase">
                Navigation
              </span>
            )}
            <Button
              variant="ghost"
              size="icon"
              aria-label={sidebarCollapsed ? 'Expand navigation' : 'Collapse navigation'}
              className="text-foreground-muted hover:bg-surface-muted hover:text-foreground size-7"
              onClick={toggleSidebar}
            >
              {sidebarCollapsed ? <IconChevronRight size={18} /> : <IconChevronLeft size={18} />}
            </Button>
          </div>

          <nav
            aria-label="Main navigation"
            className="flex-1 scrollbar-thin space-y-3 overflow-y-auto py-1.5"
          >
            {visibleNavigation.map((group) => (
              <section key={group.id} aria-labelledby={`${group.id}-navigation-label`}>
                {group.label && !compactSidebar ? (
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
                      compactSidebar && 'justify-center px-1.5',
                    )

                    const content = (
                      <>
                        <Icon size={16} className="shrink-0" aria-hidden="true" />
                        {compactSidebar ? null : (
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
                        title={compactSidebar ? item.label : undefined}
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
              className={cn('justify-start px-2.5', compactSidebar && 'justify-center px-0')}
              onClick={() => setLogoutConfirmOpen(true)}
            >
              <IconLogout size={16} />
              {compactSidebar ? null : 'Sign out'}
            </Button>
          </div>
        </aside>
      )}

      <div
        className={cn(
          'flex h-dvh min-w-0 flex-col overflow-hidden transition-[padding] duration-200',
          !hideSidebar && (sidebarCollapsed ? 'lg:pl-14' : 'lg:pl-60'),
        )}
      >
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">{children}</div>
      </div>

      <ConfirmDialog
        open={logoutConfirmOpen}
        tone="danger"
        title="Sign out of Bomach?"
        description="You will need to log in again to continue working in this workspace."
        confirmLabel="Sign out"
        cancelLabel="Stay signed in"
        onCancel={() => setLogoutConfirmOpen(false)}
        onConfirm={async () => {
          setLogoutConfirmOpen(false)
          await handleSignOut()
        }}
      />
    </div>
  )
}
