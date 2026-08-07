import { Outlet } from '@tanstack/react-router'

import { operationsNavigation } from '@/app/navigation'

import { AppShell } from './AppShell'

export function OperationsLayout() {
  return (
    <AppShell navigation={operationsNavigation}>
      <Outlet />
    </AppShell>
  )
}
