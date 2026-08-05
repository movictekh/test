import type { Meta, StoryObj } from '@storybook/react-vite'

import { Breadcrumbs } from './Breadcrumbs'

const meta = {
  title: 'Shared/Breadcrumbs',
  component: Breadcrumbs,
  args: {
    items: [
      { label: 'Command Center', to: '/app/dashboard' },
      { label: 'Commercial Operations' },
      { label: 'Service Requests' },
    ],
  },
} satisfies Meta<typeof Breadcrumbs>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {}
