import { z } from 'zod'

export const loginSchema = z.object({
  email: z.string().trim().email('Enter a valid email address.'),
  password: z.string().min(1, 'Password is required.'),
})

export const twoFactorSchema = z.object({
  code: z.string().regex(/^\d{6}$/, 'Enter the six-digit verification code.'),
})

export type LoginFormValues = z.infer<typeof loginSchema>
export type TwoFactorFormValues = z.infer<typeof twoFactorSchema>
