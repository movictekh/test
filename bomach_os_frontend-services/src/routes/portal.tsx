import { createFileRoute, redirect } from '@tanstack/react-router'

/**
 * The Client Portal is a separate application.
 *
 * This legacy parent route remains only so old internal bookmarks fail safely
 * inside the staff application instead of mounting client-owned UI.
 */
export const Route = createFileRoute('/portal')({
  beforeLoad: () => {
    return redirect({
      to: '/app/dashboard',
      replace: true,
    })
  },
  component: () => null,
})
