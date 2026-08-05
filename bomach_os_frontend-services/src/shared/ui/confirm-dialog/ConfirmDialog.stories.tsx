import type { Meta, StoryObj } from '@storybook/react-vite'
import { useState } from 'react'

import { Button } from '@/shared/ui/button'

import { ConfirmDialog } from './ConfirmDialog'

function ConfirmDialogDemo({ tone }: { tone: 'warning' | 'danger' }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="p-6">
      <Button variant={tone === 'danger' ? 'danger' : 'primary'} onClick={() => setOpen(true)}>
        Open confirmation
      </Button>
      <ConfirmDialog
        open={open}
        tone={tone}
        title={tone === 'danger' ? 'Cancel this service order?' : 'Submit quotation for approval?'}
        description={
          tone === 'danger'
            ? 'The order will stop moving through its workflow. This action must be audited.'
            : 'The quotation will become read-only while the assigned approver reviews it.'
        }
        confirmLabel={tone === 'danger' ? 'Cancel order' : 'Submit for approval'}
        onCancel={() => setOpen(false)}
        onConfirm={() => setOpen(false)}
      />
    </div>
  )
}

const meta = {
  title: 'Shared/ConfirmDialog',
  component: ConfirmDialogDemo,
} satisfies Meta<typeof ConfirmDialogDemo>

export default meta

type Story = StoryObj<typeof meta>

export const Warning: Story = {
  args: {
    tone: 'warning',
  },
}

export const Destructive: Story = {
  args: {
    tone: 'danger',
  },
}
