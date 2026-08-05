import { PERMISSIONS } from '@/app/permissions'

import type { NavigationGroup } from './navigation.types'

export const operationsNavigation = [
  {
    id: 'overview',
    items: [
      {
        id: 'dashboard',
        label: 'Command Center',
        icon: 'dashboard',
        to: '/app/dashboard',
        permissions: [PERMISSIONS.dashboardRead],
        exact: true,
      },
    ],
  },
  {
    id: 'service-administration',
    label: 'Service Administration',
    items: [
      {
        id: 'service-catalogue',
        label: 'Service Catalogue',
        icon: 'services',
        permissions: [PERMISSIONS.serviceRead],
        disabled: true,
      },
      {
        id: 'calculators',
        label: 'Calculator Library',
        icon: 'calculator',
        permissions: [PERMISSIONS.serviceRead],
        disabled: true,
      },
      {
        id: 'request-forms',
        label: 'Request Forms',
        icon: 'form',
        permissions: [PERMISSIONS.serviceRead],
        disabled: true,
      },
      {
        id: 'workflows',
        label: 'Workflow Designer',
        icon: 'workflow',
        permissions: [PERMISSIONS.serviceRead],
        disabled: true,
      },
      {
        id: 'branches',
        label: 'Branch Activation',
        icon: 'branches',
        permissions: [PERMISSIONS.serviceRead],
        disabled: true,
      },
    ],
  },
  {
    id: 'commercial',
    label: 'Commercial Operations',
    items: [
      {
        id: 'requests',
        label: 'Service Requests',
        icon: 'requests',
        permissions: [PERMISSIONS.requestRead],
        disabled: true,
      },
      {
        id: 'quotations',
        label: 'Quotations',
        icon: 'quotations',
        permissions: [PERMISSIONS.quoteRead],
        disabled: true,
      },
      {
        id: 'invoices',
        label: 'Invoices and Payments',
        icon: 'invoices',
        permissions: [PERMISSIONS.invoiceRead],
        disabled: true,
      },
      {
        id: 'approvals',
        label: 'Approval Queue',
        icon: 'approvals',
        permissions: [PERMISSIONS.approvalRead],
        disabled: true,
      },
    ],
  },
  {
    id: 'fulfilment',
    label: 'Fulfilment',
    items: [
      {
        id: 'orders',
        label: 'Service Orders',
        icon: 'orders',
        permissions: [PERMISSIONS.orderRead],
        disabled: true,
      },
      {
        id: 'tasks',
        label: 'Execution Tasks',
        icon: 'tasks',
        permissions: [PERMISSIONS.taskRead],
        disabled: true,
      },
      {
        id: 'deliverables',
        label: 'Deliverables',
        icon: 'deliverables',
        permissions: [PERMISSIONS.deliverableRead],
        disabled: true,
      },
    ],
  },
  {
    id: 'intelligence',
    label: 'Experience and Intelligence',
    items: [
      {
        id: 'feedback',
        label: 'Feedback and Quality',
        icon: 'feedback',
        permissions: [PERMISSIONS.reportRead],
        disabled: true,
      },
      {
        id: 'reports',
        label: 'Reports and Analytics',
        icon: 'reports',
        permissions: [PERMISSIONS.reportRead],
        disabled: true,
      },
      {
        id: 'audit',
        label: 'Audit Log',
        icon: 'audit',
        permissions: [PERMISSIONS.auditRead],
        disabled: true,
      },
    ],
  },
] as const satisfies readonly NavigationGroup[]

export const clientPortalNavigation = [
  {
    id: 'portal-overview',
    items: [
      {
        id: 'portal-dashboard',
        label: 'Portal Dashboard',
        icon: 'portal',
        to: '/portal/dashboard',
        permissions: [PERMISSIONS.portalRead],
        exact: true,
      },
    ],
  },
  {
    id: 'portal-services',
    label: 'My Services',
    items: [
      {
        id: 'portal-requests',
        label: 'My Requests',
        icon: 'requests',
        permissions: [PERMISSIONS.portalRead],
        disabled: true,
      },
      {
        id: 'portal-orders',
        label: 'My Orders',
        icon: 'orders',
        permissions: [PERMISSIONS.portalRead],
        disabled: true,
      },
      {
        id: 'portal-payments',
        label: 'Payments',
        icon: 'payments',
        permissions: [PERMISSIONS.portalRead],
        disabled: true,
      },
      {
        id: 'portal-documents',
        label: 'Documents',
        icon: 'documents',
        permissions: [PERMISSIONS.portalRead],
        disabled: true,
      },
      {
        id: 'portal-approvals',
        label: 'Approvals',
        icon: 'approvals',
        permissions: [PERMISSIONS.portalRead],
        disabled: true,
      },
    ],
  },
] as const satisfies readonly NavigationGroup[]
