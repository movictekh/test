import {
  Outlet,
  createRootRouteWithContext,
  type ErrorComponentProps,
} from '@tanstack/react-router'

import type { RouterContext } from '@/app/router/router'
import { ErrorState } from '@/shared/ui/error-state'

function RootComponent() {
  return <Outlet />
}

function RootErrorComponent({ error, reset }: ErrorComponentProps) {
  return (
    <main className="bg-background grid min-h-screen place-items-center p-6">
      <div className="w-full max-w-xl">
        <ErrorState
          title="The application could not continue"
          description={error.message}
          onRetry={reset}
        />
      </div>
    </main>
  )
}

function NotFoundComponent() {
  return (
    <main className="bg-background grid min-h-screen place-items-center p-6">
      <div className="w-full max-w-xl">
        <ErrorState
          title="Page not found"
          description="The page you requested does not exist in the current frontend foundation."
        />
      </div>
    </main>
  )
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootComponent,
  errorComponent: RootErrorComponent,
  notFoundComponent: NotFoundComponent,
})
