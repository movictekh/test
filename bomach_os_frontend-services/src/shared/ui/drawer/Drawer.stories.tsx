import type { Meta, StoryObj } from '@storybook/react-vite'
import { useState } from 'react'

import { Button } from '@/shared/ui/button'

import { Drawer } from './Drawer'

function DrawerDemo() {
  const [open, setOpen] = useState(false)

  return (
    <div className="p-6">
      <Button onClick={() => setOpen(true)}>Open drawer</Button>
      <Drawer
        open={open}
        title="Request filters"
        description="Apply filters without leaving the current register."
        onClose={() => setOpen(false)}
        footer={<Button onClick={() => setOpen(false)}>Apply filters</Button>}
      >
        <p className="text-foreground-muted text-sm">
          Branch, service, owner, status, and date filters will appear here.
        </p>
      </Drawer>
    </div>
  )
}

const meta = {
  title: 'Shared/Drawer',
  component: DrawerDemo,
} satisfies Meta<typeof DrawerDemo>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {}
