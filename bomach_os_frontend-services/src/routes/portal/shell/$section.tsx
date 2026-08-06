import { createFileRoute } from '@tanstack/react-router'
import { IconArrowLeft } from '@tabler/icons-react'

import { clientPortalNavigation, findNavigationItemByPath } from '@/app/navigation'
import { PERMISSIONS, requireRoutePermission } from '@/app/permissions'
import { ModuleShellPage } from '@/modules/foundation/pages/ModuleShellPage'

function formatSectionTitle(section: string): string {
  return section
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export const Route = createFileRoute('/portal/shell/$section')({
  beforeLoad: ({ context, location }) => {
    const matchingItem = findNavigationItemByPath(clientPortalNavigation, location.pathname)

    return requireRoutePermission({
      auth: context.auth,
      permissions: matchingItem?.permissions ?? [PERMISSIONS.portalRead],
    })
  },
  component: PortalShellRoute,
})

function PortalShellRoute() {
  const { section } = Route.useParams()
  const title = formatSectionTitle(section)

  return (
    <ModuleShellPage
      eyebrow="Client Portal"
      title={title}
      description="This client shell is wired into the layout and ready for the portal module."
      backTo="/portal/dashboard"
      backLabel="Back to portal"
      footerNote={
        <div className="flex items-start gap-3">
          <span className="bg-brand-50 text-brand-700 grid size-10 shrink-0 place-items-center rounded-full">
            <IconArrowLeft size={18} aria-hidden="true" />
          </span>
          <div>
            <p className="text-foreground text-sm font-semibold">{title}</p>
            <p className="text-foreground-subtle mt-1 text-xs leading-5">
              Use this shell for the customer-facing workflow when it is ready.
            </p>
          </div>
        </div>
      }
    />
  )
}
