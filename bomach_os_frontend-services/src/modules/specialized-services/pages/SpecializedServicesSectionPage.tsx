import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { IconFilePlus } from '@tabler/icons-react'

import { commercialQueries } from '@/modules/commercial/api/commercial.queries'
import { fulfillmentQueries } from '@/modules/fulfillment/api/fulfillment.queries'
import {
  CompactPageToolbar,
  CompactActionButton,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'
import { DashboardSkeleton, ErrorState } from '@/shared/ui'
import { presentError } from '@/shared/errors'
import { specializedServicesQueries } from '../api/specialized-services.queries'
import { SpecializedServiceControlScreen } from '../screens/SpecializedServiceControlScreen'
import type {
  SpecializedProfileId,
  SpecializedServicesSection,
} from '../types/specialized-services.types'
import '../styles/specialized-services.css'

const meta: Record<SpecializedServicesSection, { title: string; breadcrumb: string }> = {
  'real-estate-inventory': {
    title: 'Real Estate Inventory',
    breadcrumb: 'Specialized services / Real estate',
  },
  'survey-engineering-others': {
    title: 'Survey / Engineering / Others',
    breadcrumb: 'Specialized Services / Survey / Engineering / Others',
  },
}

export function SpecializedServicesSectionPage({
  section,
}: {
  section: SpecializedServicesSection
}) {
  const navigate = useNavigate()
  const q = useQuery(specializedServicesQueries.workspace())
  const fq = useQuery(fulfillmentQueries.workspace())
  const cq = useQuery(commercialQueries.workspace())
  const [profileId, setProfileId] = useState<SpecializedProfileId>('survey')

  if (q.isPending || fq.isPending || cq.isPending)
    return (
      <ModulePageStatus title={meta[section].title} breadcrumb={meta[section].breadcrumb}>
        <DashboardSkeleton />
      </ModulePageStatus>
    )

  if (q.isError || fq.isError || cq.isError) {
    const e = presentError(q.error ?? fq.error ?? cq.error, 'page-load')
    return (
      <ModulePageStatus title={meta[section].title} breadcrumb={meta[section].breadcrumb}>
        <ErrorState
          title={e.title}
          description={e.message}
          onRetry={() => {
            void q.refetch()
            void fq.refetch()
            void cq.refetch()
          }}
        />
      </ModulePageStatus>
    )
  }

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title={meta[section].title}
          breadcrumb={meta[section].breadcrumb}
          primaryAction={
            <CompactActionButton
              tone="primary"
              onClick={() =>
                void navigate({
                  to: '/app/$section',
                  params: { section: 'service-requests' },
                })
              }
            >
              <IconFilePlus size={14} />
              New Request
            </CompactActionButton>
          }
        />
      }
    >
      <SpecializedServiceControlScreen
        profiles={q.data.profiles}
        selectedId={profileId}
        requests={cq.data.requests}
        orders={fq.data.orders}
        onSelect={setProfileId}
        onOpenOrder={() =>
          void navigate({ to: '/app/$section', params: { section: 'service-orders' } })
        }
      />
    </ModulePageFrame>
  )
}
