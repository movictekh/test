import { describe, expect, it } from 'vitest'

import { parseRecordSearch } from './$section'

describe('app section search parser', () => {
  it('preserves Service Catalogue router state', () => {
    expect(
      parseRecordSearch({
        search: 'survey',
        status: 'active',
        division: 'Engineering',
        page: '3',
      }),
    ).toMatchObject({
      search: 'survey',
      status: 'active',
      division: 'Engineering',
      page: 3,
    })
  })

  it('drops invalid Catalogue page values', () => {
    expect(parseRecordSearch({ page: '0' }).page).toBeUndefined()
    expect(parseRecordSearch({ page: 'abc' }).page).toBeUndefined()
  })

  it('continues preserving existing record deep links', () => {
    expect(
      parseRecordSearch({
        request: 'REQ-1',
        invoice: 'INV-9',
        search: 'estate',
      }),
    ).toMatchObject({
      request: 'REQ-1',
      invoice: 'INV-9',
      search: 'estate',
    })
  })
  it('normalizes accidentally quoted identifier search values', () => {
    expect(
      parseRecordSearch({
        service: '"1"',
        estate: "'12'",
        request: '"REQ-1"',
      }),
    ).toMatchObject({
      service: '1',
      estate: '12',
      request: 'REQ-1',
    })
  })
})
