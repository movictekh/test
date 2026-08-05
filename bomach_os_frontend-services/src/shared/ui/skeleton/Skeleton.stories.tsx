import type { Meta, StoryObj } from '@storybook/react-vite'

import { AppShellSkeleton } from './AppShellSkeleton'
import { DashboardSkeleton } from './DashboardSkeleton'
import { FormSkeleton } from './FormSkeleton'
import { PageSkeleton } from './PageSkeleton'
import { TableSkeleton } from './TableSkeleton'

const meta = {
  title: 'Shared/Skeletons',
  component: PageSkeleton,
  parameters: {
    layout: 'fullscreen',
  },
} satisfies Meta<typeof PageSkeleton>

export default meta

type Story = StoryObj<typeof meta>

export const Page: Story = {}

export const Dashboard: Story = {
  render: () => <DashboardSkeleton />,
}

export const Table: Story = {
  render: () => (
    <div className="p-6">
      <TableSkeleton />
    </div>
  ),
}

export const Form: Story = {
  render: () => (
    <div className="max-w-4xl p-6">
      <FormSkeleton />
    </div>
  ),
}

export const ApplicationShell: Story = {
  render: () => <AppShellSkeleton />,
}
