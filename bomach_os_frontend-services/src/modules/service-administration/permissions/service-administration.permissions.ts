import type { AuthUser } from '@/app/auth'
import { PERMISSIONS, hasPermission, hasPermissions } from '@/app/permissions'

export interface ServiceAdministrationCapabilities {
  canListServices: boolean
  canViewService: boolean
  canCreateService: boolean
  canUpdateService: boolean
  canDeleteService: boolean
  canListCategories: boolean
  canCreateInitialServiceSetup: boolean
  canConfigureService: boolean

  canListPricingConfigs: boolean
  canCreatePricingConfig: boolean
  canUpdatePricingConfig: boolean

  canListRequestForms: boolean
  canCreateRequestForm: boolean
  canUpdateRequestForm: boolean

  canListWorkflows: boolean
  canCreateWorkflow: boolean
  canUpdateWorkflow: boolean

  canListBranchActivations: boolean
  canUpdateBranchActivations: boolean

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
      [
        PERMISSIONS.servicesCreate,
        PERMISSIONS.categoriesList,
        PERMISSIONS.serviceSubservicesUpdate,
        PERMISSIONS.serviceRequestFormsCreate,
      ],
      'all',
    ),

    // The current mock Configure Service workspace saves several backend
    // resources together. Until API-1 splits that persistence into real
    // endpoint mutations, require all affected update permissions.
    canConfigureService: hasPermissions(
      user,
      [
        PERMISSIONS.servicesUpdate,
        PERMISSIONS.serviceSubservicesUpdate,
        PERMISSIONS.serviceRequestFormsUpdate,
        PERMISSIONS.servicePricingConfigsUpdate,
        PERMISSIONS.serviceWorkflowsUpdate,
        PERMISSIONS.serviceBranchActivationsUpdate,
      ],
      'all',
    ),

    canListPricingConfigs: hasPermission(user, PERMISSIONS.servicePricingConfigsList),
    canCreatePricingConfig: hasPermission(user, PERMISSIONS.servicePricingConfigsCreate),
    canUpdatePricingConfig: hasPermission(user, PERMISSIONS.servicePricingConfigsUpdate),

    canListRequestForms: hasPermission(user, PERMISSIONS.serviceRequestFormsList),
    canCreateRequestForm: hasPermission(user, PERMISSIONS.serviceRequestFormsCreate),
    canUpdateRequestForm: hasPermission(user, PERMISSIONS.serviceRequestFormsUpdate),

    canListWorkflows: hasPermission(user, PERMISSIONS.serviceWorkflowsList),
    canCreateWorkflow: hasPermission(user, PERMISSIONS.serviceWorkflowsCreate),
    canUpdateWorkflow: hasPermission(user, PERMISSIONS.serviceWorkflowsUpdate),

    canListBranchActivations: hasPermission(user, PERMISSIONS.serviceBranchActivationsList),
    canUpdateBranchActivations: hasPermission(user, PERMISSIONS.serviceBranchActivationsUpdate),

    canCreateServiceRequest: hasPermission(user, PERMISSIONS.serviceRequestsCreate),
  }
}
