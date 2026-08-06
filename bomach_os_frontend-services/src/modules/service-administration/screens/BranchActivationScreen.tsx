import { useMemo, useState } from 'react'

import type {
  BranchActivation,
  SaveBranchActivationMatrixInput,
  ServiceCatalogueItem,
} from '../types/service-administration.types'

const branchNames = ['Enugu', 'Port Harcourt', 'Lagos', 'Abuja'] as const

function toBranchId(branchName: string) {
  return branchName.toLowerCase().replace(/[^a-z0-9]+/g, '-')
}

export function BranchActivationScreen({
  services,
  activations,
  saving,
  onSave,
}: {
  services: ServiceCatalogueItem[]
  activations: BranchActivation[]
  saving: boolean
  onSave: (input: SaveBranchActivationMatrixInput) => void
}) {
  const initialMatrix = useMemo(
    () =>
      Object.fromEntries(
        services.flatMap((service) =>
          branchNames.map((branchName) => {
            const activation = activations.find(
              (item) => item.serviceId === service.id && item.branchName === branchName,
            )
            const active =
              activation?.state === 'active' ||
              (!activation && service.branchNames.includes(branchName))

            return [`${service.id}:${branchName}`, active]
          }),
        ),
      ) as Record<string, boolean>,
    [activations, services],
  )

  const [matrix, setMatrix] = useState(initialMatrix)
  const [previousInitialMatrix, setPreviousInitialMatrix] = useState(initialMatrix)

  if (initialMatrix !== previousInitialMatrix) {
    setPreviousInitialMatrix(initialMatrix)
    setMatrix(initialMatrix)
  }

  const toggle = (serviceId: string, branchName: string) => {
    const key = `${serviceId}:${branchName}`
    setMatrix((current) => ({
      ...current,
      [key]: !(current[key] ?? false),
    }))
  }

  const save = () => {
    onSave({
      updates: services.flatMap((service) =>
        branchNames.map((branchName) => ({
          serviceId: service.id,
          serviceName: service.name,
          branchId: toBranchId(branchName),
          branchName,
          active: matrix[`${service.id}:${branchName}`] ?? false,
          slaDays: service.slaDays ?? 5,
        })),
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
            disabled={saving}
            onClick={save}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>

        <div className="service-admin-table-wrap">
          <table className="service-admin-table service-admin-branch-table">
            <thead>
              <tr>
                <th>Service</th>
                {branchNames.map((branchName) => (
                  <th key={branchName}>{branchName}</th>
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

                  {branchNames.map((branchName) => {
                    const key = `${service.id}:${branchName}`
                    const active = matrix[key] ?? false

                    return (
                      <td key={branchName}>
                        <label className="service-admin-branch-check">
                          <input
                            type="checkbox"
                            checked={active}
                            onChange={() => toggle(service.id, branchName)}
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
      </section>
    </div>
  )
}
