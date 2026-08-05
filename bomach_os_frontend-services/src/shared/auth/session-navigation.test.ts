import { describe, expect, it } from 'vitest'

import { buildSessionExpiredLoginUrl } from './session-navigation'

describe('buildSessionExpiredLoginUrl', () => {
  it('preserves a safe internal destination', () => {
    expect(buildSessionExpiredLoginUrl('/app/dashboard?tab=mine')).toBe(
      '/login?reason=session-expired&redirect=%2Fapp%2Fdashboard%3Ftab%3Dmine',
    )
  })

  it('rejects login and external-looking destinations', () => {
    expect(buildSessionExpiredLoginUrl('/login')).toBe('/login?reason=session-expired')
    expect(buildSessionExpiredLoginUrl('//malicious.example')).toBe('/login?reason=session-expired')
  })
})
