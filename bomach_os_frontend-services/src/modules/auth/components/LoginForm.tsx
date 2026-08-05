import { useForm } from '@tanstack/react-form'
import { useNavigate, useRouter } from '@tanstack/react-router'
import { useState } from 'react'

import { getAuthenticatedHome, useAuth } from '@/app/auth'
import { Alert, Button, FormControl, Input } from '@/shared/ui'

import { loginSchema, twoFactorSchema } from '../schemas/login.schema'

interface LoginFormProps {
  redirectTo?: string
}

export function LoginForm({ redirectTo }: LoginFormProps) {
  const auth = useAuth()
  const router = useRouter()
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)
  const [twoFactorSession, setTwoFactorSession] = useState<string | null>(null)
  const [twoFactorMessage, setTwoFactorMessage] = useState<string | null>(null)

  const loginForm = useForm({
    defaultValues: {
      email: '',
      password: '',
    },
    validators: { onSubmit: loginSchema },
    onSubmit: async ({ value }) => {
      setFormError(null)

      try {
        const result = await auth.login(value)

        if (result.type === 'two-factor-required') {
          setTwoFactorSession(result.sessionToken)
          setTwoFactorMessage(result.detail)
          return
        }

        await router.invalidate()
        if (redirectTo) router.history.push(redirectTo)
        else if (result.user)
          await navigate({ to: getAuthenticatedHome(result.user), replace: true })
      } catch (error) {
        setFormError(error instanceof Error ? error.message : 'Login could not be completed.')
      }
    },
  })

  const twoFactorForm = useForm({
    defaultValues: { code: '' },
    validators: { onSubmit: twoFactorSchema },
    onSubmit: async ({ value }) => {
      if (!twoFactorSession) return
      setFormError(null)

      try {
        const user = await auth.verifyTwoFactor(twoFactorSession, value.code)
        await router.invalidate()

        if (redirectTo) router.history.push(redirectTo)
        else await navigate({ to: getAuthenticatedHome(user), replace: true })
      } catch (error) {
        setFormError(error instanceof Error ? error.message : 'The code could not be verified.')
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
        {formError ? (
          <Alert tone="danger" title="Verification failed" description={formError} />
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
                onChange={(event) => field.handleChange(event.target.value.replace(/\D/g, ''))}
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
            setFormError(null)
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
      {formError ? <Alert tone="danger" title="Login failed" description={formError} /> : null}

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
              onChange={(event) => field.handleChange(event.target.value)}
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
              onChange={(event) => field.handleChange(event.target.value)}
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
