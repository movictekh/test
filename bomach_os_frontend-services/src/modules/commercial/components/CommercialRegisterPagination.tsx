interface CommercialRegisterPaginationProps {
  countLabel: string
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}

/**
 * Shared pagination for Commercial registers.
 *

 */
export function CommercialRegisterPagination({
  countLabel,
  page,
  totalPages,
  onPageChange,
}: CommercialRegisterPaginationProps) {
  return (
    <div className="commercial-table-pagination">
      <div className="commercial-table-pagination-summary">
        <span className="commercial-table-pagination-count">{countLabel}</span>
        <span className="commercial-table-pagination-divider" aria-hidden="true" />
        <span>
          Page <b>{page}</b> of <b>{totalPages}</b>
        </span>
      </div>

      <div className="commercial-table-pagination-actions">
        <button
          type="button"
          className="commercial-btn commercial-btn-small"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        <button
          type="button"
          className="commercial-btn commercial-btn-small"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  )
}
