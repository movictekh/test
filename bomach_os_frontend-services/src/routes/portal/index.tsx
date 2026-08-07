import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/portal/')({
  beforeLoad: () => {
    return redirect({
      to: '/app/dashboard',
      replace: true,
    })
  },
  component: () => null,
})
