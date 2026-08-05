import { createFileRoute } from '@tanstack/react-router'

import { requireAuthenticatedUser } from '@/app/auth'
import { ClientPortalLayout } from '@/app/layouts'

export const Route = createFileRoute('/portal')({
  beforeLoad: ({ context, location }) => {
    requireAuthenticatedUser({
      auth: context.auth,
      locationHref: location.href,
      allowedKinds: ['client'],
    })
  },
  component: ClientPortalLayout,
})
