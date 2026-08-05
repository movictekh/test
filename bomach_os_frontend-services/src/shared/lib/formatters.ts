const nigeriaCurrencyFormatter = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  maximumFractionDigits: 0,
})

const compactNigeriaCurrencyFormatter = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  notation: 'compact',
  maximumFractionDigits: 1,
})

const dateFormatter = new Intl.DateTimeFormat('en-NG', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

export function formatCurrency(value: number, compact = false): string {
  const formatter = compact ? compactNigeriaCurrencyFormatter : nigeriaCurrencyFormatter
  return formatter.format(value)
}

export function formatDate(value: string | number | Date): string {
  const date = value instanceof Date ? value : new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Invalid date'
  }

  return dateFormatter.format(date)
}
