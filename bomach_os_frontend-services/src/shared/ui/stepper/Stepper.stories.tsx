import type { Meta, StoryObj } from '@storybook/react-vite'

import { Stepper } from './Stepper'

const steps = [
  { id: 'request', label: 'Request', status: 'complete' },
  { id: 'quote', label: 'Quotation', status: 'complete' },
  { id: 'payment', label: 'Payment', status: 'current' },
  { id: 'order', label: 'Service Order', status: 'upcoming' },
  { id: 'delivery', label: 'Delivery', status: 'upcoming' },
] as const

const meta = {
  title: 'Shared/Stepper',
  component: Stepper,
  args: { steps },
} satisfies Meta<typeof Stepper>

export default meta
type Story = StoryObj<typeof meta>

export const Horizontal: Story = {}
export const Vertical: Story = { args: { orientation: 'vertical' } }
