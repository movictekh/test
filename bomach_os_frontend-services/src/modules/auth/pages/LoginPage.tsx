import { IconArrowRight, IconInfoCircle, IconLock } from '@tabler/icons-react'
import { useNavigate, useRouter } from '@tanstack/react-router'
import { useState, type FormEvent } from 'react'

import { getAuthenticatedHome, useAuth, type MockAuthProfile } from '@/app/auth'
import { AuthLayout } from '@/app/layouts'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card, CardContent } from '@/shared/ui/card'
import { FormControl } from '@/shared/ui/form-control'
import { Input } from '@/shared/ui/input'
import { Select } from '@/shared/ui/select'

interface LoginPageProps {
  redirectTo?: string
}

const profileEmail: Record<MockAuthProfile, string> = {
  'service-administrator': 'service.admin@bomach.local',
  client: 'client@bomach.local',
}

export function LoginPage({ redirectTo }: LoginPageProps) {
  const [profile, setProfile] = useState<MockAuthProfile>('service-administrator')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { signInAsProfile } = useAuth()
  const router = useRouter()
  const navigate = useNavigate()

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)

    try {
      const user = await signInAsProfile(profile)
      await router.invalidate()

      if (redirectTo) {
        router.history.push(redirectTo)
        return
      }

      await navigate({
        to: getAuthenticatedHome(user),
        replace: true,
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title="Sign in to continue"
      description="Use the temporary UI profiles while the real authentication API is being prepared."
    >
      <Card>
        <CardContent className="p-5 sm:p-6">
          <div className="rounded-control border-brand-200 bg-brand-50 mb-5 flex items-start gap-3 border p-3">
            <IconInfoCircle
              size={18}
              className="text-brand-700 mt-0.5 shrink-0"
              aria-hidden="true"
            />
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-brand-800 text-xs font-bold">UI authentication mode</p>
                <Badge tone="info">Temporary</Badge>
              </div>
              <p className="text-brand-700/80 mt-1 text-xs leading-5">
                This stores only a mock profile in localStorage. Replace it with the backend session
                flow before production.
              </p>
            </div>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <FormControl id="login-profile" label="Workspace profile" required>
              <Select
                id="login-profile"
                value={profile}
                onChange={(event) => setProfile(event.target.value as MockAuthProfile)}
              >
                <option value="service-administrator">Service Administrator</option>
                <option value="client">Client Portal User</option>
              </Select>
            </FormControl>

            <FormControl id="login-email" label="Email address" required>
              <Input id="login-email" type="email" value={profileEmail[profile]} readOnly />
            </FormControl>

            <FormControl
              id="login-password"
              label="Password"
              description="Any value is accepted in the temporary UI authentication mode."
              required
            >
              <Input id="login-password" type="password" defaultValue="demo-password" required />
            </FormControl>

            <Button type="submit" fullWidth isLoading={isSubmitting}>
              <IconLock size={17} aria-hidden="true" />
              Enter workspace
              <IconArrowRight size={17} aria-hidden="true" />
            </Button>
          </form>
        </CardContent>
      </Card>

      <p className="text-foreground-subtle mt-5 text-center text-xs">
        Route visibility improves the interface. The backend remains responsible for real
        authorization.
      </p>
    </AuthLayout>
  )
}
