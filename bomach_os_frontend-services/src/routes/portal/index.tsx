import { Navigate, createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/portal/')({
  component: () => <Navigate to="/portal/dashboard" replace />,
})
