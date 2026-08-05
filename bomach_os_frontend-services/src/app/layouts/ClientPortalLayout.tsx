import { Outlet } from '@tanstack/react-router'

import { clientPortalNavigation } from '@/app/navigation'

import { AppShell } from './AppShell'

export function ClientPortalLayout() {
  return (
    <AppShell navigation={clientPortalNavigation} variant="portal">
      <Outlet />
    </AppShell>
  )
}
