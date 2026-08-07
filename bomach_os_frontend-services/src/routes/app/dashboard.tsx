import { createFileRoute } from '@tanstack/react-router'

import { PERMISSIONS, requireRoutePermission } from '@/app/permissions'
import { OperationsDashboardPage } from '@/modules/dashboard'

export const Route = createFileRoute('/app/dashboard')({
  beforeLoad: ({ context }) => {
    return requireRoutePermission({
      auth: context.auth,
      permissions: [PERMISSIONS.dashboardView],
    })
  },
  component: OperationsDashboardPage,
})
