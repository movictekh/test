import { useMemo, useState } from 'react'

import { AccessLockIcon } from '@/shared/ui/module-controls'
import type {
  BranchActivation,
  SaveBranchActivationMatrixInput,
  ServiceCatalogueItem,
} from '../types/service-administration.types'
import type { BranchOption } from '../mappers/branch-activation.mapper'

export function BranchActivationScreen({
  services,
  branches,
  activations,
  saving,
  onSave,
}: {
  services: ServiceCatalogueItem[]
  branches: BranchOption[]
  activations: BranchActivation[]
  saving: boolean
  onSave?: (input: SaveBranchActivationMatrixInput) => void
}) {
  const canEdit = Boolean(onSave)
  const initialMatrix = useMemo(
    () =>
      Object.fromEntries(
        services.flatMap((service) =>
          branches.map((branch) => {
            const activation = activations.find(
              (item) => item.serviceId === service.id && Number(item.branchId) === branch.id,
            )
            return [`${service.id}:${branch.id}`, activation?.state === 'active']
          }),
        ),
      ) as Record<string, boolean>,
    [activations, branches, services],
  )

  const [matrix, setMatrix] = useState(initialMatrix)
  const [previousInitialMatrix, setPreviousInitialMatrix] = useState(initialMatrix)

  if (initialMatrix !== previousInitialMatrix) {
    setPreviousInitialMatrix(initialMatrix)
    setMatrix(initialMatrix)
  }

  const toggle = (serviceId: string, branchId: number) => {
    const key = `${serviceId}:${branchId}`
    setMatrix((current) => ({ ...current, [key]: !(current[key] ?? false) }))
  }

  const save = () => {
    if (!onSave) return
    onSave({
      updates: services.flatMap((service) =>
        branches.flatMap((branch) => {
          const key = `${service.id}:${branch.id}`
          const active = matrix[key] ?? false
          const wasActive = initialMatrix[key] ?? false
          if (active === wasActive) return []

          const existing = activations.find(
            (activation) =>
              activation.serviceId === service.id && Number(activation.branchId) === branch.id,
          )

          return [
            {
              serviceId: service.id,
              serviceName: service.name,
              branchId: String(branch.id),
              branchName: branch.name,
              active,
              slaDays: service.slaDays ?? 5,
              capacity: existing?.capacity ?? null,
              clientVisible: existing?.clientVisible ?? true,
              activatedAt: existing?.activatedAt ?? null,
            },
          ]
        }),
      ),
    })
  }

  return (
    <div className="service-admin-page service-admin-content">
      <section className="service-admin-card service-admin-branch-card">
        <div className="service-admin-card-header">
          <div>
            <div className="service-admin-card-title">Branch Service Activation</div>
            <div className="service-admin-card-subtitle">
              Availability, capacity and default SLA by branch
            </div>
          </div>
          <button
            type="button"
            className="service-admin-button service-admin-button-primary"
            disabled={!canEdit || saving || services.length === 0 || branches.length === 0}
            title={
              !canEdit
                ? 'You do not have permission to update branch activations'
                : services.length === 0 || branches.length === 0
                  ? 'Add services and branches before saving'
                  : undefined
            }
            onClick={save}
          >
            <AccessLockIcon show={!canEdit} />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>

        {branches.length === 0 ? (
          <div className="service-admin-notice service-admin-notice-yellow">
            No branches are configured yet. Add at least one active branch to manage service
            availability, capacity, and default SLAs.
          </div>
        ) : null}

        <div className="service-admin-table-wrap">
          <table className="service-admin-table service-admin-branch-table">
            <thead>
              <tr>
                <th>Service</th>
                {branches.map((branch) => (
                  <th key={branch.id}>{branch.name}</th>
                ))}
                <th>SLA</th>
                <th>Capacity</th>
              </tr>
            </thead>
            <tbody>
              {services.length === 0 ? (
                <tr>
                  <td colSpan={Math.max(3, branches.length + 3)}>
                    <div className="service-admin-empty-table-state" role="status">
                      <div className="service-admin-card-title">
                        No services available for branch activation
                      </div>
                      <div className="service-admin-card-subtitle mt-1">
                        Create the first Service to populate this matrix. Branch availability,
                        default SLA and capacity will stay in this same table layout.
                      </div>
                    </div>
                  </td>
                </tr>
              ) : null}
              {services.map((service) => (
                <tr key={service.id}>
                  <td>
                    <b>{service.name}</b>
                    <div className="service-admin-row-subtitle">{service.division}</div>
                  </td>
                  {branches.map((branch) => {
                    const key = `${service.id}:${branch.id}`
                    const active = matrix[key] ?? false
                    return (
                      <td key={branch.id}>
                        <label className="service-admin-branch-check">
                          <input
                            type="checkbox"
                            checked={active}
                            disabled={!canEdit}
                            onChange={() => toggle(service.id, branch.id)}
                          />
                          <span className="service-admin-branch-check-label">
                            {active ? 'Active' : 'Off'}
                          </span>
                        </label>
                      </td>
                    )
                  })}
                  <td>{service.slaDays ?? 5}d</td>
                  <td>
                    <span className="service-admin-pill service-admin-pill-green">Available</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
