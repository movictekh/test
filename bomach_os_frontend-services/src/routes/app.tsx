import { createFileRoute } from '@tanstack/react-router'

import { requireAuthenticatedUser } from '@/app/auth'
import { OperationsLayout } from '@/app/layouts'

export const Route = createFileRoute('/app')({
  beforeLoad: ({ context, location }) => {
    return requireAuthenticatedUser({
      auth: context.auth,
      locationHref: location.href,
      allowedKinds: ['staff'],
    })
  },
  component: OperationsLayout,
})
