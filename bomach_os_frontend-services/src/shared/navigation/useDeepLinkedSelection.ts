import { useState } from 'react'

/**
 * Merge URL deep-link ids with local selection without syncing via useEffect.
 * Closing dismisses the current deep-link until the URL param changes.
 */
export function useDeepLinkedSelection(deepLinkId: string | undefined) {
  const [manualId, setManualId] = useState<string | null>(null)
  const [dismissedDeepLink, setDismissedDeepLink] = useState<string | null>(null)

  const selectedId =
    manualId ?? (deepLinkId && deepLinkId !== dismissedDeepLink ? deepLinkId : null)

  const select = (id: string | null) => {
    if (id === null) {
      if (deepLinkId && selectedId === deepLinkId) {
        setDismissedDeepLink(deepLinkId)
      }
      setManualId(null)
      return
    }

    setDismissedDeepLink(null)
    setManualId(id)
  }

  return [selectedId, select] as const
}
