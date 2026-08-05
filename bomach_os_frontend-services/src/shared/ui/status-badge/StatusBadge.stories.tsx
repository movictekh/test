import type { Meta, StoryObj } from '@storybook/react-vite'

import { StatusBadge } from './StatusBadge'

const meta = {
  title: 'Shared/StatusBadge',
  component: StatusBadge,
} satisfies Meta<typeof StatusBadge>

export default meta

type Story = StoryObj<typeof meta>

export const Active: Story = {
  args: {
    status: 'active',
  },
}

export const AwaitingApproval: Story = {
  args: {
    status: 'awaiting-approval',
  },
}

export const QualityReview: Story = {
  args: {
    status: 'quality-review',
  },
}

export const Overdue: Story = {
  args: {
    status: 'overdue',
  },
}

export const CustomDomainStatus: Story = {
  args: {
    label: 'Site Assessment',
    tone: 'purple',
  },
}
