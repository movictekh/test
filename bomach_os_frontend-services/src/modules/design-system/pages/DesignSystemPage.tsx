import { IconBell, IconTrash } from '@tabler/icons-react'
import { useState } from 'react'

import {
  Alert,
  Breadcrumbs,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  ConfirmDialog,
  Dialog,
  Drawer,
  PageHeader,
  ProgressBar,
  StatusBadge,
  Stepper,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Tooltip,
  useToast,
} from '@/shared/ui'
import { ModuleScrollArea } from '@/shared/ui/module-controls'

const lifecycleSteps = [
  { id: 'request', label: 'Request', status: 'complete' },
  { id: 'quote', label: 'Quotation', status: 'complete' },
  { id: 'payment', label: 'Payment', status: 'current' },
  { id: 'order', label: 'Service Order', status: 'upcoming' },
  { id: 'delivery', label: 'Delivery', status: 'upcoming' },
] as const

export function DesignSystemPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const toast = useToast()

  return (
    <ModuleScrollArea>
      <PageHeader
        eyebrow="Phase 2"
        title="Design System Showcase"
        description="The approved visual building blocks that future Bomach business modules should reuse."
        actions={
          <Button
            onClick={() =>
              toast.success('Design-system toast', {
                description: 'The global notification system is working.',
              })
            }
          >
            Show toast
          </Button>
        }
      />

      <main className="space-y-6 p-4 sm:p-5 lg:p-7">
        <Breadcrumbs
          items={[{ label: 'Command Center', to: '/app/dashboard' }, { label: 'Design System' }]}
        />

        <Alert
          tone="info"
          title="Phase 2 visual review"
          description="Review the shared component states and interaction patterns."
        />

        <section className="grid gap-5 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Actions and statuses</CardTitle>
                <CardDescription>
                  Shared components use semantic intent rather than raw colour names.
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="flex flex-wrap gap-2">
                <Button>Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="danger">Danger</Button>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge status="active" />
                <StatusBadge status="awaiting-approval" />
                <StatusBadge status="quality-review" />
                <StatusBadge status="overdue" />
              </div>
              <ProgressBar value={68} label="Service order progress" showValue />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>Overlays</CardTitle>
                <CardDescription>
                  Dialogs, drawers, confirmations, and tooltips follow one interaction pattern.
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button onClick={() => setDialogOpen(true)}>Open dialog</Button>
              <Button variant="outline" onClick={() => setDrawerOpen(true)}>
                Open drawer
              </Button>
              <Button variant="danger" onClick={() => setConfirmOpen(true)}>
                <IconTrash size={16} />
                Confirm action
              </Button>
              <Tooltip content="This is a reusable accessible tooltip">
                <Button size="icon" variant="outline" aria-label="Notification information">
                  <IconBell size={17} />
                </Button>
              </Tooltip>
            </CardContent>
          </Card>
        </section>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Lifecycle and detail navigation</CardTitle>
              <CardDescription>Stepper and tabs support operational detail pages.</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-7">
            <Stepper steps={lifecycleSteps} />
            <Tabs defaultValue="overview">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="activities">Activities</TabsTrigger>
                <TabsTrigger value="documents">Documents</TabsTrigger>
              </TabsList>
              <TabsContent value="overview">The record summary will appear here.</TabsContent>
              <TabsContent value="activities">The activity journal will appear here.</TabsContent>
              <TabsContent value="documents">
                Deliverables and supporting documents will appear here.
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </main>

      <Dialog
        open={dialogOpen}
        title="Reusable dialog"
        description="Use this for forms, previews, details, and other non-confirmation content."
        onClose={() => setDialogOpen(false)}
        footer={<Button onClick={() => setDialogOpen(false)}>Done</Button>}
      >
        <p className="text-foreground-muted text-sm leading-6">
          Business modules supply the content. The shared dialog owns focus, escape handling,
          scrolling, overlay behaviour, and visual structure.
        </p>
      </Dialog>

      <Drawer
        open={drawerOpen}
        title="Reusable drawer"
        description="Useful for notifications, filters, details, and mobile workflows."
        onClose={() => setDrawerOpen(false)}
      >
        <p className="text-foreground-muted text-sm">
          Drawer content belongs to the feature that opens it.
        </p>
      </Drawer>

      <ConfirmDialog
        open={confirmOpen}
        tone="danger"
        title="Delete this draft?"
        description="This example shows the destructive confirmation pattern."
        confirmLabel="Delete draft"
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => {
          setConfirmOpen(false)
          toast.success('Draft deleted')
        }}
      />
    </ModuleScrollArea>
  )
}
