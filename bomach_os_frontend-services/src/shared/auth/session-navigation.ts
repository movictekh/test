const LOGIN_PATH = '/login'

export function buildSessionExpiredLoginUrl(currentPath: string): string {
  const search = new URLSearchParams({ reason: 'session-expired' })

  if (
    currentPath.startsWith('/') &&
    !currentPath.startsWith('//') &&
    !currentPath.startsWith(LOGIN_PATH)
  ) {
    search.set('redirect', currentPath)
  }

  return `${LOGIN_PATH}?${search.toString()}`
}

export function redirectToSessionExpiredLogin(): void {
  if (typeof window === 'undefined') return
  if (window.location.pathname === LOGIN_PATH) return

  const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`

  window.location.replace(buildSessionExpiredLoginUrl(currentPath))
}
