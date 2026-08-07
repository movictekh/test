import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/portal/shell/$section')({
  beforeLoad: () => {
    return redirect({
      to: '/app/dashboard',
      replace: true,
    })
  },
  component: () => null,
})
