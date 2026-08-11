import { IconMessageStar } from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { commercialQueries } from '@/modules/commercial/api/commercial.queries'
import { fulfillmentQueries } from '@/modules/fulfillment/api/fulfillment.queries'
import {
  CompactPageToolbar,
  CompactActionButton,
  ModulePageFrame,
  ModulePageStatus,
} from '@/shared/ui/module-controls'
import { presentError } from '@/shared/errors'
import { DashboardSkeleton, ErrorState, useToast } from '@/shared/ui'
import { useDeepLinkedSelection, type AppRecordSearch } from '@/shared/navigation'

import { experienceIntelligenceApi } from '../api/experience-intelligence.api'
import { experienceIntelligenceKeys } from '../api/experience-intelligence.keys'
import { experienceIntelligenceQueries } from '../api/experience-intelligence.queries'
import { AuditLogScreen } from '../screens/AuditLogScreen'
import { FeedbackQualityScreen } from '../screens/FeedbackQualityScreen'
import { ReportsAnalyticsScreen } from '../screens/ReportsAnalyticsScreen'
import type {
  CreateFeedbackInput,
  ExperienceIntelligenceSection,
  UpdateFeedbackInput,
} from '../types/experience-intelligence.types'
import {
  deriveFeedbackSummary,
  deriveReportSnapshot,
} from '../workspaces/experience-intelligence.rules'
import { FeedbackDetailWorkspace } from '../workspaces/FeedbackDetailWorkspace'
import { RecordFeedbackWorkspace } from '../workspaces/RecordFeedbackWorkspace'
import '../styles/experience-intelligence.css'

const metadata: Record<ExperienceIntelligenceSection, { title: string; breadcrumb: string }> = {
  'feedback-quality': {
    title: 'Feedback & Quality',
    breadcrumb: 'Client experience / Quality',
  },
  'reports-analytics': {
    title: 'Reports & Analytics',
    breadcrumb: 'Intelligence / Performance',
  },
  'audit-log': {
    title: 'Audit Log',
    breadcrumb: 'Governance / Accountability',
  },
}

export function ExperienceIntelligenceSectionPage({
  section,
  recordSearch,
}: {
  section: ExperienceIntelligenceSection
  recordSearch?: AppRecordSearch
}) {
  const queryClient = useQueryClient()
  const toast = useToast()

  const experienceQuery = useQuery(experienceIntelligenceQueries.workspace())
  const commercialQuery = useQuery(commercialQueries.workspace())
  const fulfillmentQuery = useQuery(fulfillmentQueries.workspace())

  const [recordFeedbackOpen, setRecordFeedbackOpen] = useState(false)
  const [selectedFeedbackId, setSelectedFeedbackId] = useDeepLinkedSelection(recordSearch?.feedback)

  const updateCache = (workspace: NonNullable<typeof experienceQuery.data>) => {
    queryClient.setQueryData(experienceIntelligenceKeys.workspace(), workspace)
  }

  const createFeedback = useMutation({
    mutationFn: (input: CreateFeedbackInput) => experienceIntelligenceApi.createFeedback(input),
    onSuccess: (workspace) => {
      updateCache(workspace)
      setRecordFeedbackOpen(false)
      toast.success('Feedback recorded')
    },
    onError: (error) => {
      const presented = presentError(error, 'form-submit')
      toast.error('Feedback could not be recorded', {
        description: presented.message,
      })
    },
  })

  const updateFeedback = useMutation({
    mutationFn: ({ feedbackId, input }: { feedbackId: string; input: UpdateFeedbackInput }) =>
      experienceIntelligenceApi.updateFeedback(feedbackId, input),
    onSuccess: (workspace) => {
      updateCache(workspace)
      toast.success('Quality follow-up updated')
    },
    onError: (error) => {
      const presented = presentError(error, 'background-action')
      toast.error('Feedback could not be updated', {
        description: presented.message,
      })
    },
  })

  const selectedFeedback = useMemo(() => {
    if (!selectedFeedbackId || !experienceQuery.data) return null
    return experienceQuery.data.feedback.find((item) => item.id === selectedFeedbackId) ?? null
  }, [experienceQuery.data, selectedFeedbackId])

  if (experienceQuery.isPending || commercialQuery.isPending || fulfillmentQuery.isPending) {
    return (
      <ModulePageStatus title={metadata[section].title} breadcrumb={metadata[section].breadcrumb}>
        <DashboardSkeleton />
      </ModulePageStatus>
    )
  }

  if (experienceQuery.isError || commercialQuery.isError || fulfillmentQuery.isError) {
    const sourceError = experienceQuery.error ?? commercialQuery.error ?? fulfillmentQuery.error
    const presented = presentError(sourceError, 'page-load')

    return (
      <ModulePageStatus title={metadata[section].title} breadcrumb={metadata[section].breadcrumb}>
        <ErrorState
          title={presented.title}
          description={presented.message}
          onRetry={() => {
            void experienceQuery.refetch()
            void commercialQuery.refetch()
            void fulfillmentQuery.refetch()
          }}
        />
      </ModulePageStatus>
    )
  }

  const page = metadata[section]
  const feedbackSummary = deriveFeedbackSummary(experienceQuery.data.feedback)
  const report = deriveReportSnapshot(
    commercialQuery.data,
    fulfillmentQuery.data,
    experienceQuery.data.feedback,
  )

  return (
    <>
      <ModulePageFrame
        header={
          <CompactPageToolbar
            title={page.title}
            breadcrumb={page.breadcrumb}
            primaryAction={
              section === 'feedback-quality' ? (
                <CompactActionButton tone="primary" onClick={() => setRecordFeedbackOpen(true)}>
                  <IconMessageStar size={14} /> Record Feedback
                </CompactActionButton>
              ) : undefined
            }
          />
        }
      >
        {section === 'feedback-quality' ? (
          <FeedbackQualityScreen
            feedback={experienceQuery.data.feedback}
            summary={feedbackSummary}
            onOpen={(feedback) => setSelectedFeedbackId(feedback.id)}
          />
        ) : section === 'reports-analytics' ? (
          <ReportsAnalyticsScreen report={report} />
        ) : (
          <AuditLogScreen events={experienceQuery.data.audit} />
        )}

        {recordFeedbackOpen ? (
          <RecordFeedbackWorkspace
            orders={fulfillmentQuery.data.orders}
            saving={createFeedback.isPending}
            onClose={() => setRecordFeedbackOpen(false)}
            onSubmit={(input) => createFeedback.mutate(input)}
          />
        ) : null}

        {selectedFeedback ? (
          <FeedbackDetailWorkspace
            feedback={selectedFeedback}
            saving={updateFeedback.isPending}
            onClose={() => setSelectedFeedbackId(null)}
            onSave={(input) =>
              updateFeedback.mutate({
                feedbackId: selectedFeedback.id,
                input,
              })
            }
          />
        ) : null}
      </ModulePageFrame>
    </>
  )
}
