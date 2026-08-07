const nigeriaNumberFormatter = new Intl.NumberFormat('en-NG', {
  maximumFractionDigits: 0,
})

const dateFormatter = new Intl.DateTimeFormat('en-NG', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

/**
 * Naira display matching Service Operations HTML `money()`:
 * - under ₦1M → full amount (₦3,200,000)
 * - ₦1M+ → abbreviated (₦11.3M / ₦4M)
 * - ₦1B+ → abbreviated (₦1.5B)
 */
export function formatCurrency(value: number): string {
  const amount = Number(value) || 0

  if (amount >= 1_000_000_000) {
    return `₦${(amount / 1_000_000_000).toFixed(1)}B`
  }

  if (amount >= 1_000_000) {
    const millions = amount / 1_000_000
    return `₦${millions.toFixed(amount % 1_000_000 ? 1 : 0)}M`
  }

  return `₦${nigeriaNumberFormatter.format(amount)}`
}

export function formatDate(value: string | number | Date): string {
  const date = value instanceof Date ? value : new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Invalid date'
  }

  return dateFormatter.format(date)
}
