import type { Meta, StoryObj } from '@storybook/react-vite'

import { Button } from '@/shared/ui/button'

import { Alert } from './Alert'

const meta = {
  title: 'Shared/Alert',
  component: Alert,
  args: {
    title: 'Information required',
    description: 'Add the missing details before this request can continue.',
  },
} satisfies Meta<typeof Alert>

export default meta

type Story = StoryObj<typeof meta>

export const Information: Story = {
  args: {
    tone: 'info',
  },
}

export const Success: Story = {
  args: {
    tone: 'success',
    title: 'Payment confirmed',
    description: 'The invoice balance and service-order readiness have been updated.',
  },
}

export const Warning: Story = {
  args: {
    tone: 'warning',
    title: 'Client approval is still required',
    description: 'This deliverable cannot move to completion until the client responds.',
  },
}

export const Danger: Story = {
  args: {
    tone: 'danger',
    title: 'Quotation submission failed',
    description: 'Review the highlighted information and try again.',
  },
}

export const WithActions: Story = {
  args: {
    tone: 'warning',
    title: 'This quotation expires tomorrow',
    description: 'Send a reminder to the client or extend the validity period.',
    actions: (
      <>
        <Button size="sm">Send reminder</Button>
        <Button size="sm" variant="outline">
          Extend validity
        </Button>
      </>
    ),
  },
}
