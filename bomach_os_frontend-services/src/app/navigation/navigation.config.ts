import { PERMISSIONS } from '@/app/permissions'

import type { NavigationGroup, NavigationPath } from './navigation.types'

const appShellRoute = '/app/shell/$section' as NavigationPath
const portalShellRoute = '/portal/shell/$section' as NavigationPath

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
        to: appShellRoute,
        params: { section: 'service-catalogue' },
        permissions: [PERMISSIONS.serviceRead],
      },
      {
        id: 'calculators',
        label: 'Calculator Library',
        icon: 'calculator',
        to: appShellRoute,
        params: { section: 'calculator-library' },
        permissions: [PERMISSIONS.serviceRead],
      },
      {
        id: 'request-form-builder',
        label: 'Request Form Builder',
        icon: 'form',
        to: appShellRoute,
        params: { section: 'request-form-builder' },
        permissions: [PERMISSIONS.serviceRead],
      },
      {
        id: 'workflows',
        label: 'Workflow Designer',
        icon: 'workflow',
        to: appShellRoute,
        params: { section: 'workflow-designer' },
        permissions: [PERMISSIONS.serviceRead],
      },
      {
        id: 'branches',
        label: 'Branch Activation',
        icon: 'branches',
        to: appShellRoute,
        params: { section: 'branch-activation' },
        permissions: [PERMISSIONS.serviceRead],
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
        to: appShellRoute,
        params: { section: 'service-requests' },
        permissions: [PERMISSIONS.requestRead],
      },
      {
        id: 'quotations',
        label: 'Quotations & Proposals',
        icon: 'quotations',
        to: appShellRoute,
        params: { section: 'quotations-proposals' },
        permissions: [PERMISSIONS.quoteRead],
      },
      {
        id: 'invoices',
        label: 'Invoices and Payments',
        icon: 'invoices',
        to: appShellRoute,
        params: { section: 'invoices-payments' },
        permissions: [PERMISSIONS.invoiceRead],
      },
      {
        id: 'approvals',
        label: 'Approval Queue',
        icon: 'approvals',
        to: appShellRoute,
        params: { section: 'approval-queue' },
        permissions: [PERMISSIONS.approvalRead],
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
        to: appShellRoute,
        params: { section: 'service-orders' },
        permissions: [PERMISSIONS.orderRead],
      },
      {
        id: 'tasks',
        label: 'Execution Tasks',
        icon: 'tasks',
        to: appShellRoute,
        params: { section: 'execution-tasks' },
        permissions: [PERMISSIONS.taskRead],
      },
      {
        id: 'deliverables',
        label: 'Deliverables',
        icon: 'deliverables',
        to: appShellRoute,
        params: { section: 'deliverables' },
        permissions: [PERMISSIONS.deliverableRead],
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
        to: appShellRoute,
        params: { section: 'feedback-quality' },
        permissions: [PERMISSIONS.reportRead],
      },
      {
        id: 'reports',
        label: 'Reports and Analytics',
        icon: 'reports',
        to: appShellRoute,
        params: { section: 'reports-analytics' },
        permissions: [PERMISSIONS.reportRead],
      },
      {
        id: 'audit',
        label: 'Audit Log',
        icon: 'audit',
        to: appShellRoute,
        params: { section: 'audit-log' },
        permissions: [PERMISSIONS.auditRead],
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
        to: portalShellRoute,
        params: { section: 'my-requests' },
        permissions: [PERMISSIONS.portalRead],
      },
      {
        id: 'portal-orders',
        label: 'My Orders',
        icon: 'orders',
        to: portalShellRoute,
        params: { section: 'my-orders' },
        permissions: [PERMISSIONS.portalRead],
      },
      {
        id: 'portal-payments',
        label: 'Payments',
        icon: 'payments',
        to: portalShellRoute,
        params: { section: 'payments' },
        permissions: [PERMISSIONS.portalRead],
      },
      {
        id: 'portal-documents',
        label: 'Documents',
        icon: 'documents',
        to: portalShellRoute,
        params: { section: 'documents' },
        permissions: [PERMISSIONS.portalRead],
      },
      {
        id: 'portal-approvals',
        label: 'Approvals',
        icon: 'approvals',
        to: portalShellRoute,
        params: { section: 'approvals' },
        permissions: [PERMISSIONS.portalRead],
      },
    ],
  },
] as const satisfies readonly NavigationGroup[]
