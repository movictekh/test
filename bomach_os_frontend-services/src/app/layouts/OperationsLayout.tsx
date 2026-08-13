import { Outlet } from '@tanstack/react-router'

import { RequireAuth } from '@/app/auth'
import { operationsNavigation } from '@/app/navigation'

import { AppShell } from './AppShell'

export function OperationsLayout() {
  return (
    <RequireAuth allowedKinds={['staff']}>
      <AppShell navigation={operationsNavigation}>
        <Outlet />
      </AppShell>
    </RequireAuth>
  )
}
