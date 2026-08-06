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
  IconSearch,
  IconSettings,
  IconShieldCheck,
  IconUserScreen,
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
  portal: IconUserScreen,
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

          <NotificationPanel />

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
          sidebarCollapsed ? 'w-14' : 'w-52',
          mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="border-border flex items-center justify-between gap-1.5 border-b px-2 py-1.5">
          {sidebarCollapsed ? null : (
            <span className="text-foreground-muted text-[0.5rem] leading-none font-bold tracking-[0.14em] uppercase">
              Navigation
            </span>
          )}
          <Button
            variant="ghost"
            size="icon"
            aria-label={sidebarCollapsed ? 'Expand navigation' : 'Collapse navigation'}
            className="text-foreground-muted hover:bg-surface-muted hover:text-foreground size-7"
            onClick={() => setSidebarCollapsed((current) => !current)}
          >
            {sidebarCollapsed ? <IconChevronRight size={18} /> : <IconChevronLeft size={18} />}
          </Button>
        </div>

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
                        <span className="min-w-0 flex-1 truncate">{item.label}</span>
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
          'min-h-screen pt-16 transition-[padding] duration-200',
          sidebarCollapsed ? 'lg:pl-14' : 'lg:pl-52',
        )}
      >
        {children}
      </div>
    </div>
  )
}
