import { PERMISSIONS } from '@/app/permissions'

import type { NavigationGroup, NavigationPath } from './navigation.types'

const appSectionRoute = '/app/$section' as NavigationPath

export const operationsNavigation = [
  {
    id: 'overview',
    items: [
      {
        id: 'dashboard',
        label: 'Command Center',
        icon: 'dashboard',
        to: '/app/dashboard',
        permissions: [PERMISSIONS.dashboardView],
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
        permissions: [PERMISSIONS.servicesList],
      },
      {
        id: 'calculators',
        label: 'Calculator Library',
        icon: 'calculator',
        to: appSectionRoute,
        params: { section: 'calculator-library' },
        permissions: [PERMISSIONS.servicePricingConfigsList],
      },
      {
        id: 'request-form-builder',
        label: 'Request Form Builder',
        icon: 'form',
        to: appSectionRoute,
        params: { section: 'request-form-builder' },
        permissions: [PERMISSIONS.serviceRequestFormsList],
      },
      {
        id: 'workflows',
        label: 'Workflow Designer',
        icon: 'workflow',
        to: appSectionRoute,
        params: { section: 'workflow-designer' },
        permissions: [PERMISSIONS.serviceWorkflowsList],
      },
      {
        id: 'branches',
        label: 'Branch Activation',
        icon: 'branches',
        to: appSectionRoute,
        params: { section: 'branch-activation' },
        permissions: [PERMISSIONS.serviceBranchActivationsList],
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
        permissions: [PERMISSIONS.serviceRequestsList],
        badge: 1,
      },
      {
        id: 'quotations',
        label: 'Quotations',
        icon: 'quotations',
        to: appSectionRoute,
        params: { section: 'quotations' },
        permissions: [PERMISSIONS.quotesList],
      },
      {
        id: 'invoices',
        label: 'Invoices & Payments',
        icon: 'invoices',
        to: appSectionRoute,
        params: { section: 'invoices-payments' },
        permissions: [PERMISSIONS.serviceInvoicesList],
      },
      {
        id: 'approvals',
        label: 'Approvals',
        icon: 'approvals',
        to: appSectionRoute,
        params: { section: 'approvals' },
        permissions: [PERMISSIONS.approvalRequestsList],
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
        permissions: [PERMISSIONS.ordersList],
      },
      {
        id: 'tasks',
        label: 'Execution Tasks',
        icon: 'tasks',
        to: appSectionRoute,
        params: { section: 'execution-tasks' },
        permissions: [PERMISSIONS.tasksList],
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
        permissions: [
          PERMISSIONS.estatesList,
          PERMISSIONS.propertiesList,
          PERMISSIONS.brokerageList,
        ],
      },
      {
        id: 'survey-engineering-others',
        label: 'Survey / Engineering / Others',
        icon: 'orders',
        to: appSectionRoute,
        params: { section: 'survey-engineering-others' },
        permissions: [PERMISSIONS.ordersList],
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
        permissions: [PERMISSIONS.reportsView],
      },
      {
        id: 'reports',
        label: 'Reports and Analytics',
        icon: 'reports',
        to: appSectionRoute,
        params: { section: 'reports-analytics' },
        permissions: [PERMISSIONS.reportsView],
      },
      {
        id: 'audit',
        label: 'Audit Log',
        icon: 'audit',
        to: appSectionRoute,
        params: { section: 'audit-log' },
        permissions: [PERMISSIONS.auditLogsList],
      },
    ],
  },
] as const satisfies readonly NavigationGroup[]
