import type { AuthUser } from '@/app/auth'
import { PERMISSIONS, hasPermission, hasPermissions } from '@/app/permissions'

export interface ServiceAdministrationCapabilities {
  canListServices: boolean
  canViewService: boolean
  canCreateService: boolean
  canUpdateService: boolean
  canDeleteService: boolean
  canListCategories: boolean
  canUpdateSubservices: boolean
  canCreateInitialServiceSetup: boolean

  canListPricingConfigs: boolean
  canViewPricingConfig: boolean
  canCreatePricingConfig: boolean
  canUpdatePricingConfig: boolean

  canListRequestForms: boolean
  canCreateRequestForm: boolean
  canUpdateRequestForm: boolean

  canListWorkflows: boolean
  canCreateWorkflow: boolean
  canUpdateWorkflow: boolean

  canListBranches: boolean
  canListRoles: boolean
  canListBranchActivations: boolean
  canUpdateBranchActivations: boolean

  canPublishService: boolean
  canCreateServiceRequest: boolean
}

export function getServiceAdministrationCapabilities(
  user: AuthUser | null,
): ServiceAdministrationCapabilities {
  return {
    canListServices: hasPermission(user, PERMISSIONS.servicesList),
    canViewService: hasPermission(user, PERMISSIONS.servicesView),
    canCreateService: hasPermission(user, PERMISSIONS.servicesCreate),
    canUpdateService: hasPermission(user, PERMISSIONS.servicesUpdate),
    canDeleteService: hasPermission(user, PERMISSIONS.servicesDelete),
    canListCategories: hasPermission(user, PERMISSIONS.categoriesList),
    canCreateInitialServiceSetup: hasPermissions(
      user,
      [PERMISSIONS.servicesCreate, PERMISSIONS.categoriesList],
      'all',
    ),
    canUpdateSubservices: hasPermission(user, PERMISSIONS.serviceSubservicesUpdate),

    canListPricingConfigs: hasPermission(user, PERMISSIONS.servicePricingConfigsList),
    canViewPricingConfig: hasPermission(user, PERMISSIONS.servicePricingConfigsView),
    canCreatePricingConfig: hasPermission(user, PERMISSIONS.servicePricingConfigsCreate),
    canUpdatePricingConfig: hasPermission(user, PERMISSIONS.servicePricingConfigsUpdate),

    canListRequestForms: hasPermission(user, PERMISSIONS.serviceRequestFormsList),
    canCreateRequestForm: hasPermission(user, PERMISSIONS.serviceRequestFormsCreate),
    canUpdateRequestForm: hasPermission(user, PERMISSIONS.serviceRequestFormsUpdate),

    canListWorkflows: hasPermission(user, PERMISSIONS.serviceWorkflowsList),
    canCreateWorkflow: hasPermission(user, PERMISSIONS.serviceWorkflowsCreate),
    canUpdateWorkflow: hasPermission(user, PERMISSIONS.serviceWorkflowsUpdate),

    canListBranches: hasPermission(user, PERMISSIONS.branchesList),
    canListRoles: hasPermission(user, PERMISSIONS.rolesList),
    canListBranchActivations: hasPermission(user, PERMISSIONS.serviceBranchActivationsList),
    canUpdateBranchActivations: hasPermission(user, PERMISSIONS.serviceBranchActivationsUpdate),

    canPublishService: hasPermission(user, PERMISSIONS.servicesUpdate),
    canCreateServiceRequest: hasPermission(user, PERMISSIONS.serviceRequestsCreate),
  }
}
