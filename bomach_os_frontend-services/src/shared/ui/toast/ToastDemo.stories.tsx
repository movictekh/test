import type { Meta, StoryObj } from '@storybook/react-vite'

import { Button } from '@/shared/ui/button'

import { ToastProvider } from './ToastProvider'
import { useToast } from './useToast'

function ToastDemo() {
  const toast = useToast()

  return (
    <div className="flex min-h-72 flex-wrap items-start gap-2 p-6">
      <Button
        onClick={() =>
          toast.success('Request created', {
            description: 'REQ-260805-021 is ready for review.',
          })
        }
      >
        Success toast
      </Button>
      <Button
        variant="outline"
        onClick={() =>
          toast.info('Draft saved', {
            description: 'Your latest changes were saved locally.',
          })
        }
      >
        Info toast
      </Button>
      <Button
        variant="outline"
        onClick={() =>
          toast.warning('Approval required', {
            description: 'A senior approver must review this quotation.',
          })
        }
      >
        Warning toast
      </Button>
      <Button
        variant="danger"
        onClick={() =>
          toast.error('Payment confirmation failed', {
            description: 'Check the reference and try again.',
          })
        }
      >
        Error toast
      </Button>
    </div>
  )
}

const meta = {
  title: 'Shared/Toast',
  component: ToastDemo,
  decorators: [
    (Story) => (
      <ToastProvider>
        <Story />
      </ToastProvider>
    ),
  ],
} satisfies Meta<typeof ToastDemo>

export default meta

type Story = StoryObj<typeof meta>

export const Demo: Story = {}
