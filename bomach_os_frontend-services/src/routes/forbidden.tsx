import { createFileRoute } from '@tanstack/react-router'

import { ForbiddenPage } from '@/app/errors/ForbiddenPage'

export const Route = createFileRoute('/forbidden')({
  component: ForbiddenPage,
})
