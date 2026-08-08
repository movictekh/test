import { useForm } from '@tanstack/react-form'
import { useRouter } from '@tanstack/react-router'
import { useEffect, useState } from 'react'

import { useAuth } from '@/app/auth'
import { operationsNavigation } from '@/app/navigation/navigation.config'
import { getAuthenticatedNavigationPath } from '@/app/navigation/navigation.utils'
import { isAuthAccessError } from '@/modules/auth/errors/auth-access-error'
import { presentError } from '@/shared/errors'
import { Alert, Button, FormControl, Input } from '@/shared/ui'

import { loginSchema, twoFactorSchema } from '../schemas/login.schema'

interface LoginFormProps {
  redirectTo?: string
  onDismissSessionContext?: () => void
  onFormAlertChange?: (hasAlert: boolean) => void
}

interface FormAlertState {
  title: string
  description: string
}

/** Prefill Service Administrator credentials in local/dev (see mocks/data/auth.mock.ts). */
const loginDefaults = import.meta.env.DEV
  ? { email: 'service.admin@bomach.local', password: 'demo-password' }
  : { email: '', password: '' }

function accessIssueAlert(error: unknown): FormAlertState | null {
  if (!isAuthAccessError(error)) return null

  if (error.issue === 'employee-profile-missing') {
    return {
      title: 'Account setup incomplete',
      description:
        'Your credentials are valid, but this account is not linked to a staff profile. Contact your system administrator to complete account provisioning.',
    }
  }

  if (error.issue === 'role-missing') {
    return {
      title: 'Access not configured',
      description:
        'Your credentials are valid, but no role has been assigned to this account. Contact your system administrator to request access.',
    }
  }

  return {
    title: 'Access denied',
    description:
      'You are not authorised to access this workspace. Contact your system administrator if you believe this is an error.',
  }
}

function toFormAlert(error: unknown, context: 'login' | 'two-factor'): FormAlertState {
  const accessAlert = accessIssueAlert(error)
  if (accessAlert) return accessAlert

  const presented = presentError(error, context)
  return {
    title: presented.title,
    description: presented.message,
  }
}

export function LoginForm({
  redirectTo,
  onDismissSessionContext,
  onFormAlertChange,
}: LoginFormProps) {
  const auth = useAuth()
  const router = useRouter()
  const [formAlert, setFormAlert] = useState<FormAlertState | null>(null)
  const [twoFactorSession, setTwoFactorSession] = useState<string | null>(null)
  const [twoFactorMessage, setTwoFactorMessage] = useState<string | null>(null)

  const clearFormAlert = () => setFormAlert(null)

  const beginSubmitAttempt = () => {
    onDismissSessionContext?.()
    clearFormAlert()
  }

  const showFormAlert = (alert: FormAlertState) => {
    onDismissSessionContext?.()
    setFormAlert(alert)
  }

  useEffect(() => {
    onFormAlertChange?.(formAlert !== null)
  }, [formAlert, onFormAlertChange])

  const loginForm = useForm({
    defaultValues: {
      email: loginDefaults.email,
      password: loginDefaults.password,
    },
    validators: { onSubmit: loginSchema },
    onSubmit: async ({ value }) => {
      beginSubmitAttempt()

      try {
        const result = await auth.login(value)

        if (result.type === 'two-factor-required') {
          setTwoFactorSession(result.sessionToken)
          setTwoFactorMessage(result.detail)
          return
        }

        await router.invalidate()

        if (result.user) {
          const destination = getAuthenticatedNavigationPath(
            operationsNavigation,
            result.user,
            redirectTo,
          )

          router.history.replace(destination ?? '/forbidden')
        }
      } catch (error) {
        showFormAlert(toFormAlert(error, 'login'))
      }
    },
  })

  const twoFactorForm = useForm({
    defaultValues: { code: '' },
    validators: { onSubmit: twoFactorSchema },
    onSubmit: async ({ value }) => {
      if (!twoFactorSession) return
      beginSubmitAttempt()

      try {
        const user = await auth.verifyTwoFactor(twoFactorSession, value.code)
        await router.invalidate()

        const destination = getAuthenticatedNavigationPath(operationsNavigation, user, redirectTo)

        router.history.replace(destination ?? '/forbidden')
      } catch (error) {
        showFormAlert(toFormAlert(error, 'two-factor'))
      }
    },
  })

  const getErrorMessage = (errors: readonly unknown[]) =>
    (errors[0] as { message?: string } | undefined)?.message

  if (twoFactorSession) {
    return (
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          event.stopPropagation()
          void twoFactorForm.handleSubmit()
        }}
      >
        {twoFactorMessage ? (
          <Alert tone="info" title="Verification required" description={twoFactorMessage} />
        ) : null}
        {formAlert ? (
          <Alert tone="danger" title={formAlert.title} description={formAlert.description} />
        ) : null}

        <twoFactorForm.Field name="code">
          {(field) => (
            <FormControl
              id="two-factor-code"
              label="Verification code"
              error={getErrorMessage(field.state.meta.errors)}
            >
              <Input
                id="two-factor-code"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                value={field.state.value}
                invalid={field.state.meta.errors.length > 0}
                onBlur={field.handleBlur}
                onChange={(event) => {
                  field.handleChange(event.target.value.replace(/\D/g, ''))
                }}
              />
            </FormControl>
          )}
        </twoFactorForm.Field>

        <twoFactorForm.Subscribe
          selector={(state) => [state.canSubmit, state.isSubmitting] as const}
        >
          {([canSubmit, isSubmitting]) => (
            <Button type="submit" fullWidth disabled={!canSubmit} isLoading={isSubmitting}>
              Verify and continue
            </Button>
          )}
        </twoFactorForm.Subscribe>

        <Button
          type="button"
          variant="ghost"
          fullWidth
          onClick={() => {
            setTwoFactorSession(null)
            setTwoFactorMessage(null)
            clearFormAlert()
          }}
        >
          Back to login
        </Button>
      </form>
    )
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault()
        event.stopPropagation()
        void loginForm.handleSubmit()
      }}
    >
      {formAlert ? (
        <Alert tone="danger" title={formAlert.title} description={formAlert.description} />
      ) : null}

      <loginForm.Field name="email">
        {(field) => (
          <FormControl
            id="login-email"
            label="Email"
            error={getErrorMessage(field.state.meta.errors)}
          >
            <Input
              id="login-email"
              type="email"
              autoComplete="email"
              value={field.state.value}
              invalid={field.state.meta.errors.length > 0}
              onBlur={field.handleBlur}
              onChange={(event) => {
                field.handleChange(event.target.value)
              }}
            />
          </FormControl>
        )}
      </loginForm.Field>

      <loginForm.Field name="password">
        {(field) => (
          <FormControl
            id="login-password"
            label="Password"
            error={getErrorMessage(field.state.meta.errors)}
          >
            <Input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={field.state.value}
              invalid={field.state.meta.errors.length > 0}
              onBlur={field.handleBlur}
              onChange={(event) => {
                field.handleChange(event.target.value)
              }}
            />
          </FormControl>
        )}
      </loginForm.Field>

      <loginForm.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting] as const}>
        {([canSubmit, isSubmitting]) => (
          <Button type="submit" fullWidth disabled={!canSubmit} isLoading={isSubmitting}>
            Sign in
          </Button>
        )}
      </loginForm.Subscribe>
    </form>
  )
}
