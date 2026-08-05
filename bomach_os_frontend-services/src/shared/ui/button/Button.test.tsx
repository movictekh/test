import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Button } from './Button'

describe('Button', () => {
  it('runs its click handler', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()

    render(<Button onClick={handleClick}>Create request</Button>)

    await user.click(screen.getByRole('button', { name: 'Create request' }))

    expect(handleClick).toHaveBeenCalledOnce()
  })

  it('is disabled while loading', () => {
    render(<Button isLoading>Saving</Button>)

    expect(screen.getByRole('button', { name: 'Saving' })).toBeDisabled()
  })
})
