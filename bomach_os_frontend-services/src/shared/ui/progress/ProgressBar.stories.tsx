import type { Meta, StoryObj } from '@storybook/react-vite'

import { ProgressBar } from './ProgressBar'

const meta = {
  title: 'Shared/ProgressBar',
  component: ProgressBar,
  args: {
    value: 68,
    label: 'Service order progress',
    showValue: true,
  },
} satisfies Meta<typeof ProgressBar>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {}
export const Success: Story = { args: { value: 100, tone: 'success' } }
export const Warning: Story = { args: { value: 42, tone: 'warning' } }
