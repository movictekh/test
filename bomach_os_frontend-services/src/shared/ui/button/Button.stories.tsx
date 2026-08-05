import type { Meta, StoryObj } from '@storybook/react-vite'

import { Button } from './Button'

const meta = {
  title: 'Foundation/Button',
  component: Button,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  args: {
    children: 'Create request',
  },
} satisfies Meta<typeof Button>

export default meta

type Story = StoryObj<typeof meta>

export const Primary: Story = {}

export const Secondary: Story = {
  args: {
    variant: 'secondary',
  },
}

export const Outline: Story = {
  args: {
    variant: 'outline',
  },
}

export const Danger: Story = {
  args: {
    variant: 'danger',
  },
}

export const Loading: Story = {
  args: {
    isLoading: true,
    children: 'Saving',
  },
}
