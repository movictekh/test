import { IconInfoCircle } from '@tabler/icons-react'
import type { Meta, StoryObj } from '@storybook/react-vite'

import { Button } from '@/shared/ui/button'

import { Tooltip } from './Tooltip'

function TooltipDemo() {
  return (
    <div className="grid min-h-48 place-items-center">
      <Tooltip content="View the latest service information">
        <Button size="icon" variant="outline" aria-label="Information">
          <IconInfoCircle size={18} />
        </Button>
      </Tooltip>
    </div>
  )
}

const meta = {
  title: 'Shared/Tooltip',
  component: TooltipDemo,
} satisfies Meta<typeof TooltipDemo>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {}
