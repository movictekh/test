import { useForm } from '@tanstack/react-form'
import type { CreateEstateInput } from '../types/specialized-services.types'
export function CreateEstateWorkspace({
  saving,
  onClose,
  onSubmit,
}: {
  saving: boolean
  onClose: () => void
  onSubmit: (input: CreateEstateInput) => void
}) {
  const form = useForm({
    defaultValues: { name: '', location: '', plotCount: 50, plotSize: 500, unitPrice: 5_000_000 },
  })
  return (
    <div className="specialized-modal-backdrop" onMouseDown={onClose}>
      <form
        className="specialized-modal"
        onMouseDown={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit(form.state.values)
        }}
      >
        <header className="specialized-modal-header">
          <h2>Add Estate</h2>
          <button type="button" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="specialized-modal-body specialized-form-grid">
          <form.Field name="name">
            {(f) => (
              <label className="specialized-field">
                <span>Estate name</span>
                <input value={f.state.value} onChange={(e) => f.handleChange(e.target.value)} />
              </label>
            )}
          </form.Field>
          <form.Field name="location">
            {(f) => (
              <label className="specialized-field">
                <span>Location</span>
                <input value={f.state.value} onChange={(e) => f.handleChange(e.target.value)} />
              </label>
            )}
          </form.Field>
          <form.Field name="plotCount">
            {(f) => (
              <label className="specialized-field">
                <span>Number of plots</span>
                <input
                  type="number"
                  value={f.state.value}
                  onChange={(e) => f.handleChange(Number(e.target.value || 0))}
                />
              </label>
            )}
          </form.Field>
          <form.Field name="plotSize">
            {(f) => (
              <label className="specialized-field">
                <span>Plot size (sqm)</span>
                <input
                  type="number"
                  value={f.state.value}
                  onChange={(e) => f.handleChange(Number(e.target.value || 0))}
                />
              </label>
            )}
          </form.Field>
          <form.Field name="unitPrice">
            {(f) => (
              <label className="specialized-field">
                <span>Unit price</span>
                <input
                  type="number"
                  value={f.state.value}
                  onChange={(e) => f.handleChange(Number(e.target.value || 0))}
                />
              </label>
            )}
          </form.Field>
        </div>
        <footer className="specialized-modal-footer">
          <button type="button" className="specialized-btn" onClick={onClose}>
            Cancel
          </button>
          <button className="specialized-btn specialized-btn-primary" disabled={saving}>
            Create Estate
          </button>
        </footer>
      </form>
    </div>
  )
}
