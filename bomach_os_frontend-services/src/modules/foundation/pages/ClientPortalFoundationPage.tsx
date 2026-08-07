import {
  IconClipboardCheck,
  IconFileDescription,
  IconReceipt,
  IconRoute,
} from '@tabler/icons-react'

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  PageHeader,
  StatCard,
} from '@/shared/ui'
import { formatCurrency } from '@/shared/lib/formatters'

export function ClientPortalFoundationPage() {
  return (
    <>
      <PageHeader
        eyebrow="Client Portal"
        title="Welcome to your service workspace"
        description="Follow your requests, payments, orders, documents, approvals, and required actions in one place."
        actions={<Button>Request a service</Button>}
      />

      <main className="space-y-6 p-4 sm:p-5 lg:p-7">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Open requests" value="2" icon={<IconRoute size={20} />} />
          <StatCard label="Active orders" value="1" icon={<IconClipboardCheck size={20} />} />
          <StatCard
            label="Outstanding balance"
            value={formatCurrency(350_000)}
            icon={<IconReceipt size={20} />}
          />
          <StatCard label="Documents" value="4" icon={<IconFileDescription size={20} />} />
        </div>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Current service activity</CardTitle>
              <CardDescription>
                This portal foundation will later load only records belonging to the authenticated
                client.
              </CardDescription>
            </div>
            <Badge tone="info">UI foundation</Badge>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="Portal modules are coming next"
              description="The protected client layout and permission boundary are ready. Requests, orders, payments, documents, and approvals will be added as their modules are built."
            />
          </CardContent>
        </Card>
      </main>
    </>
  )
}
