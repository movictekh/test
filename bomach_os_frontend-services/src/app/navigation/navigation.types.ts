import type { AppPermission, PermissionMode } from '@/app/permissions'

export type NavigationIconName =
  | 'dashboard'
  | 'services'
  | 'calculator'
  | 'form'
  | 'workflow'
  | 'branches'
  | 'requests'
  | 'quotations'
  | 'invoices'
  | 'approvals'
  | 'orders'
  | 'tasks'
  | 'deliverables'
  | 'feedback'
  | 'reports'
  | 'audit'
  | 'portal'
  | 'payments'
  | 'documents'

export type NavigationPath =
  | '/app/dashboard'
  | '/app/design-system'
  | '/portal/dashboard'
  | '/app/shell/$section'
  | '/portal/shell/$section'

export interface NavigationItem {
  id: string
  label: string
  icon: NavigationIconName
  to: NavigationPath
  params?: Record<string, string>
  permissions?: readonly AppPermission[]
  permissionMode?: PermissionMode
  badge?: string | number
  exact?: boolean
}

export interface NavigationGroup {
  id: string
  label?: string
  items: readonly NavigationItem[]
}
