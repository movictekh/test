import { IconArrowLeft, IconLockAccess } from '@tabler/icons-react'
import { useRouter } from '@tanstack/react-router'

import { useAuth } from '@/app/auth'
import { operationsNavigation } from '@/app/navigation/navigation.config'
import { getAuthenticatedNavigationPath } from '@/app/navigation/navigation.utils'
import { Button } from '@/shared/ui/button'
import { Card, CardContent } from '@/shared/ui/card'

export function ForbiddenPage() {
  const { user, signOut } = useAuth()
  const router = useRouter()

  const destination = getAuthenticatedNavigationPath(operationsNavigation, user)

  const returnToWorkspace = async () => {
    if (destination) {
      router.history.replace(destination)
      return
    }

    await signOut()
    router.history.replace('/login')
  }

  return (
    <main className="bg-background grid min-h-screen place-items-center p-5">
      <Card className="w-full max-w-xl">
        <CardContent className="p-8 text-center sm:p-10">
          <div className="bg-danger-50 text-danger-700 mx-auto grid size-14 place-items-center rounded-2xl">
            <IconLockAccess size={26} aria-hidden="true" />
          </div>
          <p className="text-danger-700 mt-5 text-xs font-extrabold tracking-[0.12em] uppercase">
            Access restricted
          </p>
          <h1 className="text-foreground mt-2 text-2xl font-black">You cannot open this area</h1>
          <p className="text-foreground-muted mx-auto mt-3 max-w-md text-sm leading-6">
            Your current account does not have permission to view this page. The backend must still
            enforce the same rule when real APIs are connected.
          </p>
          <div className="mt-7 flex justify-center">
            <Button onClick={() => void returnToWorkspace()}>
              <IconArrowLeft size={17} aria-hidden="true" />
              {destination ? 'Return to your workspace' : 'Sign out'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  )
}
