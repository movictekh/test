export const commercialMoney = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  maximumFractionDigits: 0,
})

export function requestStatusClass(status: string) {
  if (status === 'New' || status === 'Rejected') return 'commercial-pill-gray'
  if (status === 'Quoted' || status === 'Converted') return 'commercial-pill-green'
  if (
    status === 'Awaiting Quotation' ||
    status === 'Client Approval' ||
    status === 'Awaiting Client' ||
    status === 'Site Assessment'
  ) {
    return 'commercial-pill-yellow'
  }
  return 'commercial-pill-blue'
}

export function quotationStatusClass(status: string) {
  if (status === 'Accepted' || status === 'Approved') return 'commercial-pill-green'
  if (status === 'Rejected' || status === 'Expired') return 'commercial-pill-red'
  if (
    status === 'Awaiting Approval' ||
    status === 'Pending Approval' ||
    status === 'Sent' ||
    status === 'Issued'
  ) {
    return 'commercial-pill-yellow'
  }
  if (status === 'Draft') return 'commercial-pill-gray'
  return 'commercial-pill-blue'
}

export const quotationApprovers = [
  'Service Manager',
  'Head of Operations',
  'Finance Manager',
  'CEO / Founder',
] as const
