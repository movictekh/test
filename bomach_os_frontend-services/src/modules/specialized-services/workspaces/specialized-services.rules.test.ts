import { describe, expect, it } from 'vitest'
import { buildPlots, estateCounts } from './specialized-services.rules'
describe('specialized services rules', () => {
  it('builds numbered available plots', () => {
    const p = buildPlots(3, 500, 5_000_000)
    expect(p.map((x) => x.no)).toEqual(['01', '02', '03'])
    expect(p.every((x) => x.status === 'Available')).toBe(true)
  })
  it('counts inventory states', () => {
    const p = buildPlots(4, 500, 5_000_000)
    p[0]!.status = 'Sold'
    p[1]!.status = 'Reserved'
    expect(estateCounts({ id: 'E', name: 'X', location: 'Y', plots: p })).toEqual({
      total: 4,
      sold: 1,
      reserved: 1,
      available: 2,
    })
  })
})
