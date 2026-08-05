import type { Meta, StoryObj } from '@storybook/react-vite'
import { useState } from 'react'

import { Button } from '@/shared/ui/button'
import { FormControl } from '@/shared/ui/form-control'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'

import { Dialog } from './Dialog'

function DialogDemo() {
  const [open, setOpen] = useState(false)

  return (
    <div className="p-6">
      <Button onClick={() => setOpen(true)}>Open request dialog</Button>
      <Dialog
        open={open}
        title="Add request activity"
        description="Record an important client communication or internal update."
        onClose={() => setOpen(false)}
        footer={
          <>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => setOpen(false)}>Save activity</Button>
          </>
        }
      >
        <div className="space-y-4">
          <FormControl id="activity-subject" label="Subject">
            <Input id="activity-subject" placeholder="Client follow-up" />
          </FormControl>
          <FormControl id="activity-note" label="Note">
            <Textarea id="activity-note" placeholder="Add the activity details..." />
          </FormControl>
        </div>
      </Dialog>
    </div>
  )
}

const meta = {
  title: 'Shared/Dialog',
  component: DialogDemo,
} satisfies Meta<typeof DialogDemo>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {}
