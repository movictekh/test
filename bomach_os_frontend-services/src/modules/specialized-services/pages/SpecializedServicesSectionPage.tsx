import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { IconFilePlus, IconPlus } from '@tabler/icons-react'

import { commercialQueries } from '@/modules/commercial/api/commercial.queries'
import { fulfillmentQueries } from '@/modules/fulfillment/api/fulfillment.queries'
import { CompactPageToolbar, CompactActionButton, ModulePageFrame, ModulePageStatus } from '@/shared/ui/module-controls'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'
import { presentError } from '@/shared/errors'
import { specializedServicesApi } from '../api/specialized-services.api'
import { specializedServicesKeys } from '../api/specialized-services.keys'
import { specializedServicesQueries } from '../api/specialized-services.queries'
import { RealEstateInventoryScreen } from '../screens/RealEstateInventoryScreen'
import { SpecializedServiceControlScreen } from '../screens/SpecializedServiceControlScreen'
import type {
  SpecializedProfileId,
  SpecializedServicesSection,
} from '../types/specialized-services.types'
import { CreateBrokerageWorkspace } from '../workspaces/CreateBrokerageWorkspace'
import { CreateEstateWorkspace } from '../workspaces/CreateEstateWorkspace'
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
  const qc = useQueryClient()
  const toast = useToast()
  const q = useQuery(specializedServicesQueries.workspace())
  const fq = useQuery(fulfillmentQueries.workspace())
  const cq = useQuery(commercialQueries.workspace())
  const [selectedEstateId, setSelectedEstateId] = useState('')
  const [selectedPlotNo, setSelectedPlotNo] = useState<string | null>(null)
  const [estateOpen, setEstateOpen] = useState(false)
  const [propertyOpen, setPropertyOpen] = useState(false)
  const [profileId, setProfileId] = useState<SpecializedProfileId>('survey')
  const set = (w: NonNullable<typeof q.data>) =>
    qc.setQueryData(specializedServicesKeys.workspace(), w)
  const ce = useMutation({
    mutationFn: specializedServicesApi.createEstate,
    onSuccess: (w) => {
      set(w)
      setEstateOpen(false)
      toast.success('Estate created')
    },
  })
  const up = useMutation({
    mutationFn: specializedServicesApi.updatePlot,
    onSuccess: (w) => {
      set(w)
      toast.success('Plot record updated')
    },
  })
  const cp = useMutation({
    mutationFn: specializedServicesApi.createBrokerageProperty,
    onSuccess: (w) => {
      set(w)
      setPropertyOpen(false)
      toast.success('Property listing added')
    },
  })
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
  const estateId = selectedEstateId || q.data.estates[0]?.id || ''

  return (
    <>
      <ModulePageFrame
        header={
          <CompactPageToolbar
        title={meta[section].title}
        breadcrumb={meta[section].breadcrumb}
        {...(section === 'real-estate-inventory'
          ? {
              secondaryAction: (
                <CompactActionButton onClick={() => setPropertyOpen(true)}>
                  <IconPlus size={14} />
                  Add Brokerage Property
                </CompactActionButton>
              ),
              primaryAction: (
                <CompactActionButton tone="primary" onClick={() => setEstateOpen(true)}>
                  <IconPlus size={14} />
                  Add Estate
                </CompactActionButton>
              ),
            }
          : {
              primaryAction: (
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
              ),
            })}
          />
        }
      >
      {section === 'real-estate-inventory' ? (
        <RealEstateInventoryScreen
          estates={q.data.estates}
          brokerage={q.data.brokerage}
          selectedEstateId={estateId}
          selectedPlotNo={selectedPlotNo}
          onSelectEstate={(id) => {
            setSelectedEstateId(id)
            setSelectedPlotNo(null)
          }}
          onSelectPlot={setSelectedPlotNo}
          onSavePlot={(p) =>
            up.mutate({
              estateId,
              plotNo: p.no,
              status: p.status,
              client: p.client,
              price: p.price,
            })
          }
        />
      ) : (
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
      )}
      {estateOpen ? (
        <CreateEstateWorkspace
          saving={ce.isPending}
          onClose={() => setEstateOpen(false)}
          onSubmit={(x) => ce.mutate(x)}
        />
      ) : null}
      {propertyOpen ? (
        <CreateBrokerageWorkspace
          saving={cp.isPending}
          onClose={() => setPropertyOpen(false)}
          onSubmit={(x) => cp.mutate(x)}
        />
      ) : null}
      </ModulePageFrame>
    </>
  )
}
