import {
  IconActivity,
  IconBuildingStore,
  IconCash,
  IconClipboardCheck,
  IconPlus,
} from '@tabler/icons-react'
import { queryOptions, useQuery } from '@tanstack/react-query'

import { apiClient } from '@/shared/api/api-client'
import { AppShell } from '@/shared/layouts/AppShell'
import { formatCurrency } from '@/shared/lib/formatters'
import type { ApiResponse } from '@/shared/types/api'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  FormControl,
  Input,
  PageHeader,
  Select,
  Skeleton,
  StatCard,
  Textarea,
} from '@/shared/ui'

interface HealthStatus {
  status: string
  service: string
  timestamp: string
}

const healthQueryOptions = queryOptions({
  queryKey: ['foundation', 'health'],
  queryFn: () => apiClient.get<ApiResponse<HealthStatus>>('/health'),
  select: (response) => response.data,
})

export function FoundationPage() {
  const healthQuery = useQuery(healthQueryOptions)

  return (
    <AppShell>
      <PageHeader
        eyebrow="Phase 1"
        title="Frontend Foundation"
        description="Design tokens, shared components, TanStack providers, API boundaries, mocks, tests, and quality tooling."
        actions={
          <>
            <Button variant="outline">View standards</Button>
            <Button>
              <IconPlus size={17} aria-hidden="true" />
              Continue setup
            </Button>
          </>
        }
      />

      <main className="space-y-6 p-4 sm:p-5 lg:p-7">
        <section aria-labelledby="foundation-status-title">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 id="foundation-status-title" className="text-foreground text-sm font-extrabold">
                Foundation status
              </h2>
              <p className="text-foreground-subtle mt-1 text-xs">
                These cards confirm the global design language we will reuse across the module.
              </p>
            </div>
            <Badge tone={healthQuery.isSuccess ? 'success' : 'warning'}>
              {healthQuery.isSuccess ? 'Foundation online' : 'Checking foundation'}
            </Badge>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Shared components"
              value="14"
              trend={{ direction: 'up', label: 'Initial library ready' }}
              icon={<IconClipboardCheck size={20} />}
            />
            <StatCard
              label="Confirmed revenue"
              value={formatCurrency(11_300_000, true)}
              description="Example formatting utility"
              icon={<IconCash size={20} />}
            />
            <StatCard
              label="Active branches"
              value="4"
              description="Example business metric"
              icon={<IconBuildingStore size={20} />}
            />
            <StatCard
              label="Mock API"
              value={healthQuery.isSuccess ? 'Ready' : 'Pending'}
              description="MSW network layer"
              icon={<IconActivity size={20} />}
            />
          </div>
        </section>

        <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Form component foundation</CardTitle>
                <CardDescription>
                  These controls will later be connected to TanStack Form and domain schemas.
                </CardDescription>
              </div>
              <Badge tone="info">Reusable</Badge>
            </CardHeader>

            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormControl id="client-name" label="Client name" required>
                  <Input id="client-name" placeholder="Enter client or organisation" />
                </FormControl>

                <FormControl id="service" label="Service">
                  <Select id="service" defaultValue="">
                    <option value="" disabled>
                      Select a service
                    </option>
                    <option>Building Construction</option>
                    <option>Cadastral Land Survey</option>
                  </Select>
                </FormControl>

                <FormControl
                  id="scope"
                  label="Request scope"
                  description="Add enough information for the first review."
                  className="sm:col-span-2"
                >
                  <Textarea id="scope" placeholder="Describe what the client needs..." />
                </FormControl>

                <div className="flex flex-wrap gap-2 sm:col-span-2">
                  <Button>Primary action</Button>
                  <Button variant="secondary">Secondary</Button>
                  <Button variant="outline">Outline</Button>
                  <Button variant="ghost">Ghost</Button>
                  <Button variant="danger">Danger</Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>Network and page states</CardTitle>
                <CardDescription>
                  Every production page must handle loading, success, empty, and error states.
                </CardDescription>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {healthQuery.isPending ? (
                <div className="space-y-3" aria-label="Loading mock API status">
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-20 w-full" />
                </div>
              ) : healthQuery.isError ? (
                <ErrorState
                  title="Mock API unavailable"
                  description={healthQuery.error.message}
                  onRetry={() => {
                    void healthQuery.refetch()
                  }}
                />
              ) : (
                <div className="rounded-card border-success-200 bg-success-50 border p-4">
                  <p className="text-success-700 text-sm font-bold">{healthQuery.data.service}</p>
                  <p className="text-success-700/80 mt-1 text-xs">
                    Status: {healthQuery.data.status}. The UI is using the same request path that
                    the real backend will later provide.
                  </p>
                </div>
              )}

              <EmptyState
                title="No service requests yet"
                description="This is the standard empty state that registers will reuse."
                action={<Button size="sm">Create request</Button>}
              />
            </CardContent>
          </Card>
        </div>
      </main>
    </AppShell>
  )
}
