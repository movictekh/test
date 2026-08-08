import { useNavigate } from '@tanstack/react-router'
import { useCallback, useState } from 'react'

import { Alert } from '@/shared/ui'

import { LoginForm } from '../components/LoginForm'

interface LoginPageProps {
  redirectTo?: string
  reason?: 'session-expired'
}

export function LoginPage({ redirectTo, reason }: LoginPageProps) {
  const navigate = useNavigate()
  const [hasFormAlert, setHasFormAlert] = useState(false)

  const dismissSessionExpired = useCallback(() => {
    if (reason !== 'session-expired') return

    void navigate({
      to: '/login',
      search: (previous) => {
        const next = { ...previous }
        delete next.reason
        return next
      },
      replace: true,
    })
  }, [navigate, reason])

  const showSessionExpired = reason === 'session-expired' && !hasFormAlert

  return (
    <main className="min-h-screen bg-[linear-gradient(135deg,#112957,#1f3d7a_58%,#3159aa)] px-4 py-8 sm:grid sm:place-items-center">
      <section className="mx-auto w-full max-w-[420px] rounded-[22px] bg-white px-6 py-8 shadow-[0_24px_80px_rgba(4,12,32,0.35)] sm:px-[38px] sm:py-[38px]">
        <header className="mb-7 text-center">
          <div className="bg-accent-600 mx-auto grid size-12 place-items-center rounded-[14px] text-xl font-black text-white">
            B
          </div>
          <h1 className="text-foreground mt-4 text-xl font-black">Bomach Service Operations OS</h1>
          <p className="text-foreground-muted mt-2 text-xs leading-5">
            Request · Quote · Pay · Deliver · Experience
          </p>
        </header>

        {showSessionExpired ? (
          <Alert
            className="mb-4"
            tone="warning"
            title="Your session has expired"
            description="Sign in again to continue from where you stopped."
          />
        ) : null}

        <LoginForm
          {...(redirectTo ? { redirectTo } : {})}
          onDismissSessionContext={dismissSessionExpired}
          onFormAlertChange={setHasFormAlert}
        />

        <p className="text-foreground-subtle mt-6 text-center text-[0.6875rem] leading-5">
          Secure access for authorised Bomach staff and clients.
        </p>
      </section>
    </main>
  )
}
