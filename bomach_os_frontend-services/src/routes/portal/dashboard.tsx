import { createFileRoute } from '@tanstack/react-router'

import { PERMISSIONS, requireRoutePermission } from '@/app/permissions'
import { ClientPortalFoundationPage } from '@/modules/foundation/pages/ClientPortalFoundationPage'

export const Route = createFileRoute('/portal/dashboard')({
  beforeLoad: ({ context }) => {
    return requireRoutePermission({
      auth: context.auth,
      permissions: [PERMISSIONS.portalRead],
    })
  },
  component: ClientPortalFoundationPage,
})
