import { createFileRoute } from '@tanstack/react-router'

import { PERMISSIONS, requireRoutePermission } from '@/app/permissions'
import { DesignSystemPage } from '@/modules/design-system'

export const Route = createFileRoute('/app/design-system')({
  beforeLoad: ({ context }) =>
    requireRoutePermission({
      auth: context.auth,
      permissions: [PERMISSIONS.dashboardView],
    }),
  component: DesignSystemPage,
})
