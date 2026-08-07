import { PERMISSIONS } from '@/app/permissions'

import type { NavigationGroup, NavigationPath } from './navigation.types'

const appSectionRoute = '/app/$section' as NavigationPath
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
        to: appSectionRoute,
        params: { section: 'service-catalogue' },
        permissions: [PERMISSIONS.serviceRead],
      },
      {
        id: 'calculators',
        label: 'Calculator Library',
        icon: 'calculator',
        to: appSectionRoute,
        params: { section: 'calculator-library' },
        permissions: [PERMISSIONS.serviceRead],
      },
      {
        id: 'request-form-builder',
        label: 'Request Form Builder',
        icon: 'form',
        to: appSectionRoute,
        params: { section: 'request-form-builder' },
        permissions: [PERMISSIONS.serviceRead],
      },
      {
        id: 'workflows',
        label: 'Workflow Designer',
        icon: 'workflow',
        to: appSectionRoute,
        params: { section: 'workflow-designer' },
        permissions: [PERMISSIONS.serviceRead],
      },
      {
        id: 'branches',
        label: 'Branch Activation',
        icon: 'branches',
        to: appSectionRoute,
        params: { section: 'branch-activation' },
        permissions: [PERMISSIONS.serviceRead],
      },
    ],
  },
  {
    id: 'commercial',
    label: 'Commercial Flow',
    items: [
      {
        id: 'requests',
        label: 'Service Requests',
        icon: 'requests',
        to: appSectionRoute,
        params: { section: 'service-requests' },
        permissions: [PERMISSIONS.requestRead],
        badge: 1,
      },
      {
        id: 'quotations',
        label: 'Quotations',
        icon: 'quotations',
        to: appSectionRoute,
        params: { section: 'quotations' },
        permissions: [PERMISSIONS.quoteRead],
      },
      {
        id: 'invoices',
        label: 'Invoices & Payments',
        icon: 'invoices',
        to: appSectionRoute,
        params: { section: 'invoices-payments' },
        permissions: [PERMISSIONS.invoiceRead],
      },
      {
        id: 'approvals',
        label: 'Approvals',
        icon: 'approvals',
        to: appSectionRoute,
        params: { section: 'approvals' },
        permissions: [PERMISSIONS.approvalRead],
        badge: 4,
        badgeTone: 'alert',
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
        to: appSectionRoute,
        params: { section: 'service-orders' },
        permissions: [PERMISSIONS.orderRead],
      },
      {
        id: 'tasks',
        label: 'Execution Tasks',
        icon: 'tasks',
        to: appSectionRoute,
        params: { section: 'execution-tasks' },
        permissions: [PERMISSIONS.taskRead],
      },
      {
        id: 'deliverables',
        label: 'Deliverables',
        icon: 'deliverables',
        to: appSectionRoute,
        params: { section: 'deliverables' },
        permissions: [PERMISSIONS.deliverableRead],
      },
    ],
  },
  {
    id: 'specialized-services',
    label: 'Specialized Services',
    items: [
      {
        id: 'real-estate-inventory',
        label: 'Real Estate Inventory',
        icon: 'services',
        to: appSectionRoute,
        params: { section: 'real-estate-inventory' },
        permissions: [PERMISSIONS.realEstateRead],
      },
      {
        id: 'survey-engineering-others',
        label: 'Survey / Engineering / Others',
        icon: 'orders',
        to: appSectionRoute,
        params: { section: 'survey-engineering-others' },
        permissions: [PERMISSIONS.orderRead],
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
        to: appSectionRoute,
        params: { section: 'feedback-quality' },
        permissions: [PERMISSIONS.reportRead],
      },
      {
        id: 'reports',
        label: 'Reports and Analytics',
        icon: 'reports',
        to: appSectionRoute,
        params: { section: 'reports-analytics' },
        permissions: [PERMISSIONS.reportRead],
      },
      {
        id: 'audit',
        label: 'Audit Log',
        icon: 'audit',
        to: appSectionRoute,
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
