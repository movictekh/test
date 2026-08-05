import type { Meta, StoryObj } from '@storybook/react-vite'

import { Button } from '@/shared/ui/button'

import { SuccessState } from './SuccessState'

const meta = {
  title: 'Shared/SuccessState',
  component: SuccessState,
  args: {
    title: 'Service request created',
    description:
      'The request has been created and assigned to the Service Manager for the first review.',
    reference: 'REQ-260805-021',
  },
} satisfies Meta<typeof SuccessState>

export default meta

type Story = StoryObj<typeof meta>

export const Default: Story = {
  args: {
    primaryAction: <Button>View request</Button>,
    secondaryAction: <Button variant="outline">Create another</Button>,
  },
}

export const Compact: Story = {
  args: {
    compact: true,
    title: 'Payment confirmed',
    description: 'The invoice and service-order readiness have been updated.',
  },
}
