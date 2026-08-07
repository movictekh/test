import type { Estate, EstatePlot, PlotStatus } from '../types/specialized-services.types'
export function estateCounts(estate: Estate) {
  const count = (status: PlotStatus) => estate.plots.filter((plot) => plot.status === status).length
  return {
    total: estate.plots.length,
    sold: count('Sold'),
    reserved: count('Reserved'),
    available: count('Available'),
  }
}
export function buildPlots(count: number, size: number, price: number): EstatePlot[] {
  const n = Math.max(1, Math.min(500, Math.round(count)))
  return Array.from({ length: n }, (_, i) => ({
    no: String(i + 1).padStart(2, '0'),
    status: 'Available',
    size,
    client: '',
    price,
  }))
}
