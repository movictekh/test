import { createFileRoute } from '@tanstack/react-router'

import { PERMISSIONS, requireRoutePermission } from '@/app/permissions'
import { FoundationPage } from '@/modules/foundation/pages/FoundationPage'

export const Route = createFileRoute('/app/dashboard')({
  beforeLoad: ({ context }) => {
    return requireRoutePermission({
      auth: context.auth,
      permissions: [PERMISSIONS.dashboardRead],
    })
  },
  component: FoundationPage,
})
