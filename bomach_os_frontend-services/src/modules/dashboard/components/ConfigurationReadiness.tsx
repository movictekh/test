import { Card, CardContent } from '@/shared/ui'

import type { DashboardConfigurationReadiness } from '../types/dashboard.types'

export function ConfigurationReadiness({
  configuration,
}: {
  configuration: DashboardConfigurationReadiness
}) {
  const rows = [
    ['Active services', configuration.activeServices],
    ['Draft services', configuration.draftServices],
    ['Missing workflow', configuration.missingWorkflow],
    ['Missing branch activation', configuration.missingBranchActivation],
  ] as const

  return (
    <Card>
      <CardContent className="space-y-3">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-3">
            <span className="text-foreground-subtle text-xs">{label}</span>
            <span className="text-sm font-extrabold">{value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
