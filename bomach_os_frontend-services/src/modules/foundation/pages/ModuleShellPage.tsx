import { Link } from '@tanstack/react-router'
import { IconArrowLeft } from '@tabler/icons-react'
import type { ReactNode } from 'react'

import { Card, CardContent, EmptyState, PageHeader } from '@/shared/ui'
import { ModuleScrollArea } from '@/shared/ui/module-controls'

interface ModuleShellPageProps {
  eyebrow: string
  title: string
  description: string
  backTo: string
  backLabel: string
  footerNote?: ReactNode
}

export function ModuleShellPage({
  eyebrow,
  title,
  description,
  backTo,
  backLabel,
  footerNote,
}: ModuleShellPageProps) {
  return (
    <ModuleScrollArea>
      <PageHeader
        eyebrow={eyebrow}
        title={title}
        description={description}
        actions={
          <Link
            to={backTo}
            className="border-border bg-surface text-foreground hover:bg-surface-muted rounded-control inline-flex h-10 items-center gap-2 border px-4 text-sm font-semibold transition-colors"
          >
            <IconArrowLeft size={16} aria-hidden="true" />
            {backLabel}
          </Link>
        }
      />

      <main className="space-y-6 p-4 sm:p-5 lg:p-7">
        <EmptyState
          title="Empty shell ready"
          description="This route is wired into the navigation and layout. The real module can be dropped in here when the feature is built."
        />

        <div className="grid gap-4 lg:grid-cols-3">
          <Card>
            <CardContent className="space-y-2">
              <p className="text-foreground-subtle text-[0.625rem] font-bold tracking-[0.12em] uppercase">
                Route status
              </p>
              <p className="text-foreground text-sm font-semibold">Connected to sidebar</p>
              <p className="text-foreground-subtle text-xs leading-5">
                The navigation entry now opens a real page instead of a disabled placeholder.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-2">
              <p className="text-foreground-subtle text-[0.625rem] font-bold tracking-[0.12em] uppercase">
                Empty state
              </p>
              <p className="text-foreground text-sm font-semibold">No module content yet</p>
              <p className="text-foreground-subtle text-xs leading-5">
                This shell can be replaced by tables, forms, filters, and workflows when the
                corresponding feature lands.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-2">
              <p className="text-foreground-subtle text-[0.625rem] font-bold tracking-[0.12em] uppercase">
                Next step
              </p>
              <p className="text-foreground text-sm font-semibold">Build the domain screen</p>
              <p className="text-foreground-subtle text-xs leading-5">
                Use this page as the first canvas for the real service module.
              </p>
            </CardContent>
          </Card>
        </div>

        {footerNote ? (
          <Card>
            <CardContent>{footerNote}</CardContent>
          </Card>
        ) : null}
      </main>
    </ModuleScrollArea>
  )
}
