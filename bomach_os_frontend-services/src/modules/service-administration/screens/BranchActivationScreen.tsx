import { useMemo, useState } from 'react'

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
        branches.map((branch) => ({
          serviceId: service.id,
          serviceName: service.name,
          branchId: String(branch.id),
          branchName: branch.name,
          active: matrix[`${service.id}:${branch.id}`] ?? false,
          slaDays: service.slaDays ?? 5,
        })),
      ),
    })
  }

  if (services.length === 0) {
    return (
      <main className="service-admin-page service-admin-content">
        <section className="service-admin-card p-6 text-center" role="status">
          <h2 className="service-admin-card-title">No services available</h2>
          <p className="service-admin-card-subtitle mt-1">
            Create a service before configuring branch availability.
          </p>
        </section>
      </main>
    )
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
          {canEdit ? (
            <button
              type="button"
              className="service-admin-button service-admin-button-primary"
              disabled={saving}
              onClick={save}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          ) : null}
        </div>

        {branches.length === 0 ? (
          <div className="service-admin-notice service-admin-notice-yellow">
            No active branches are available from the backend.
          </div>
        ) : (
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
                            <span>{active ? 'Active' : 'Off'}</span>
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
        )}
      </section>
    </div>
  )
}
