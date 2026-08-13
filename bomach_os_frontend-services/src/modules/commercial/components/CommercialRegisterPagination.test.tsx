import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CommercialRegisterPagination } from './CommercialRegisterPagination'

describe('CommercialRegisterPagination', () => {
  it('renders paging state and changes pages', () => {
    const onPageChange = vi.fn()

    render(
      <CommercialRegisterPagination
        countLabel="24 records"
        page={2}
        totalPages={3}
        onPageChange={onPageChange}
      />,
    )

    expect(screen.getByText('24 records')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Previous' }))
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))

    expect(onPageChange).toHaveBeenNthCalledWith(1, 1)
    expect(onPageChange).toHaveBeenNthCalledWith(2, 3)
  })

  it('disables navigation at register boundaries', () => {
    const { rerender } = render(
      <CommercialRegisterPagination
        countLabel="1 record"
        page={1}
        totalPages={2}
        onPageChange={() => undefined}
      />,
    )

    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Next' })).not.toBeDisabled()

    rerender(
      <CommercialRegisterPagination
        countLabel="1 record"
        page={2}
        totalPages={2}
        onPageChange={() => undefined}
      />,
    )

    expect(screen.getByRole('button', { name: 'Previous' })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })
})
