import { IconChecks, IconLock, IconRoute } from '@tabler/icons-react'
import type { PropsWithChildren } from 'react'

interface AuthLayoutProps extends PropsWithChildren {
  title: string
  description: string
}

const benefits = [
  {
    icon: IconRoute,
    title: 'One service journey',
    description: 'Follow work from request and quotation to payment, delivery, and feedback.',
  },
  {
    icon: IconChecks,
    title: 'Clear ownership',
    description: 'Know who owns every request, approval, order, task, and deliverable.',
  },
  {
    icon: IconLock,
    title: 'Controlled access',
    description: 'Routes and actions are shown according to the authenticated user’s permissions.',
  },
] as const

export function AuthLayout({ children, title, description }: AuthLayoutProps) {
  return (
    <main className="bg-background grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
      <section className="bg-brand-700 relative hidden overflow-hidden p-10 text-white lg:flex lg:flex-col lg:justify-between xl:p-14">
        <div className="bg-brand-500/20 absolute -top-28 -right-24 size-80 rounded-full blur-3xl" />
        <div className="bg-accent-600/20 absolute -bottom-24 -left-20 size-72 rounded-full blur-3xl" />

        <div className="relative flex items-center gap-3">
          <div className="bg-accent-600 grid size-12 place-items-center rounded-2xl text-xl font-black">
            B
          </div>
          <div>
            <p className="text-base font-extrabold">Bomach Group</p>
            <p className="text-xs text-white/60">Service Operations OS</p>
          </div>
        </div>

        <div className="relative max-w-xl space-y-5">
          <p className="text-brand-100 text-xs font-extrabold tracking-[0.18em] uppercase">
            Connected service delivery
          </p>
          <h1 className="text-4xl leading-tight font-black text-balance xl:text-5xl">
            Turn every client request into controlled, visible, and measurable delivery.
          </h1>
          <p className="max-w-lg text-sm leading-7 text-white/70">
            The operations workspace joins commercial work, fulfilment, client experience, and
            governance in one traceable flow.
          </p>
        </div>

        <div className="relative grid gap-3 xl:grid-cols-3">
          {benefits.map((benefit) => {
            const Icon = benefit.icon

            return (
              <article
                key={benefit.title}
                className="rounded-card border border-white/10 bg-white/5 p-4"
              >
                <Icon size={20} className="text-brand-200" aria-hidden="true" />
                <h2 className="mt-3 text-sm font-bold">{benefit.title}</h2>
                <p className="mt-1.5 text-xs leading-5 text-white/60">{benefit.description}</p>
              </article>
            )
          })}
        </div>
      </section>

      <section className="flex items-center justify-center p-5 sm:p-8 lg:p-12">
        <div className="w-full max-w-md">
          <div className="mb-7 lg:hidden">
            <div className="flex items-center gap-3">
              <div className="bg-brand-600 grid size-11 place-items-center rounded-xl text-lg font-black text-white">
                B
              </div>
              <div>
                <p className="text-foreground text-sm font-extrabold">Bomach Group</p>
                <p className="text-foreground-subtle text-xs">Service Operations OS</p>
              </div>
            </div>
          </div>

          <div className="mb-7">
            <p className="text-brand-600 text-xs font-extrabold tracking-[0.12em] uppercase">
              Secure workspace
            </p>
            <h2 className="text-foreground mt-2 text-3xl font-black">{title}</h2>
            <p className="text-foreground-muted mt-2 text-sm leading-6">{description}</p>
          </div>

          {children}
        </div>
      </section>
    </main>
  )
}
