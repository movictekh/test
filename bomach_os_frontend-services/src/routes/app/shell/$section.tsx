import { createFileRoute } from '@tanstack/react-router'
import { IconArrowLeft } from '@tabler/icons-react'

import { findNavigationItemByPath, operationsNavigation } from '@/app/navigation'
import { PERMISSIONS, requireRoutePermission } from '@/app/permissions'
import { ModuleShellPage } from '@/modules/foundation/pages/ModuleShellPage'

function formatSectionTitle(section: string): string {
  return section
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export const Route = createFileRoute('/app/shell/$section')({
  beforeLoad: ({ context, location }) => {
    const matchingItem = findNavigationItemByPath(operationsNavigation, location.pathname)

    return requireRoutePermission({
      auth: context.auth,
      permissions: matchingItem?.permissions ?? [PERMISSIONS.dashboardRead],
    })
  },
  component: AppShellRoute,
})

function AppShellRoute() {
  const { section } = Route.useParams()
  const title = formatSectionTitle(section)

  return (
    <ModuleShellPage
      eyebrow="Service Operations"
      title={title}
      description="This is the first shell for the module. The full workspace will be layered in here."
      backTo="/app/dashboard"
      backLabel="Back to dashboard"
      footerNote={
        <div className="flex items-start gap-3">
          <span className="bg-brand-50 text-brand-700 grid size-10 shrink-0 place-items-center rounded-full">
            <IconArrowLeft size={18} aria-hidden="true" />
          </span>
          <div>
            <p className="text-foreground text-sm font-semibold">{title}</p>
            <p className="text-foreground-subtle mt-1 text-xs leading-5">
              The shell is ready for the real module implementation.
            </p>
          </div>
        </div>
      }
    />
  )
}
