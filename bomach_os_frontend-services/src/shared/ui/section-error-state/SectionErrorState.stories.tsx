import type { Meta, StoryObj } from '@storybook/react-vite'

import { SectionErrorState } from './SectionErrorState'

const meta = {
  title: 'Shared/SectionErrorState',
  component: SectionErrorState,
} satisfies Meta<typeof SectionErrorState>

export default meta

type Story = StoryObj<typeof meta>

export const Default: Story = {
  args: {
    title: 'Revenue summary is unavailable',
    description:
      'Requests and active orders loaded successfully, but this financial summary could not be retrieved.',
    onRetry: () => undefined,
  },
}
