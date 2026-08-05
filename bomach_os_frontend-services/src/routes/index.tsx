import { createFileRoute } from '@tanstack/react-router'

import { FoundationPage } from '@/modules/foundation/pages/FoundationPage'

export const Route = createFileRoute('/')({
  component: FoundationPage,
})
