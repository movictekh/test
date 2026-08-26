import {
  IconDownload,
  IconFileSpreadsheet,
  IconRefresh,
  IconUpload,
  IconX,
} from '@tabler/icons-react'
import { useMemo, useState } from 'react'

import { presentError } from '@/shared/errors'

import { realEstateApi } from '../real-estate/real-estate.api'
import {
  downloadEstatePropertyData,
  downloadPropertyResults,
  downloadPropertyTemplate,
  parsePropertySheetMatrix,
  PROPERTY_DATA_CONCURRENCY,
  type PropertyDataMode,
  type PropertyDataRow,
  type PropertyWorkbookData,
  readPropertyWorkbook,
} from '../real-estate/property-data'
import type { Property } from '../real-estate/real-estate.types'

type RowFilter = 'all' | 'ready' | 'issues'

async function runWithConcurrency<T>(
  values: T[],
  limit: number,
  worker: (value: T) => Promise<void>,
) {
  let cursor = 0
  const runners = Array.from({ length: Math.min(limit, values.length) }, async () => {
    while (cursor < values.length) {
      const index = cursor
      cursor += 1
      await worker(values[index])
    }
  })
  await Promise.all(runners)
}

export function PropertyDataStudioWorkspace({
  estateId,
  estateName,
  canCreate,
  canUpdate,
  onClose,
  onChanged,
}: {
  estateId: number
  estateName: string
  canCreate: boolean
  canUpdate: boolean
  onClose: () => void
  onChanged: () => Promise<void> | void
}) {
  const [mode, setMode] = useState<PropertyDataMode>('create')
  const [workbook, setWorkbook] = useState<PropertyWorkbookData | null>(null)
  const [sheetName, setSheetName] = useState('')
  const [rows, setRows] = useState<PropertyDataRow[]>([])
  const [fileErrors, setFileErrors] = useState<string[]>([])
  const [warnings, setWarnings] = useState<string[]>([])
  const [error, setError] = useState('')
  const [running, setRunning] = useState(false)
  const [loadingExisting, setLoadingExisting] = useState(false)
  const [existingProperties, setExistingProperties] = useState<Property[] | null>(null)
  const [filter, setFilter] = useState<RowFilter>('all')

  const summary = useMemo(
    () => ({
      total: rows.length,
      ready: rows.filter((row) => row.status === 'ready').length,
      invalid: rows.filter((row) => row.status === 'invalid').length,
      skipped: rows.filter((row) => row.status === 'skipped').length,
      success: rows.filter((row) => row.status === 'success').length,
      failed: rows.filter((row) => row.status === 'failed').length,
      selected: rows.filter(
        (row) => row.selected && (row.status === 'ready' || row.status === 'failed'),
      ).length,
    }),
    [rows],
  )

  const visibleRows = useMemo(() => {
    if (filter === 'ready')
      return rows.filter((row) => ['ready', 'success', 'failed', 'submitting'].includes(row.status))
    if (filter === 'issues')
      return rows.filter((row) => row.status === 'invalid' || row.status === 'failed')
    return rows
  }, [filter, rows])

  const ensureExistingProperties = async () => {
    if (existingProperties) return existingProperties
    setLoadingExisting(true)
    try {
      const loaded = await realEstateApi.listAllProperties(estateId)
      setExistingProperties(loaded)
      return loaded
    } finally {
      setLoadingExisting(false)
    }
  }

  const applySheet = (
    source: PropertyWorkbookData,
    selectedSheet: string,
    targetMode: PropertyDataMode,
    existing: Property[],
  ) => {
    const sheet = source.sheets.find((candidate) => candidate.name === selectedSheet)
    if (!sheet) {
      setRows([])
      setFileErrors(['The selected worksheet could not be found.'])
      return
    }

    const parsed = parsePropertySheetMatrix(sheet.matrix, targetMode, existing)
    setRows(parsed.rows)
    setFileErrors(parsed.fileErrors)
    setWarnings(parsed.warnings)
    setError('')
    setFilter(parsed.fileErrors.length ? 'issues' : 'all')
  }

  const resetImport = () => {
    setWorkbook(null)
    setSheetName('')
    setRows([])
    setFileErrors([])
    setWarnings([])
    setError('')
    setFilter('all')
  }

  const changeMode = (nextMode: PropertyDataMode) => {
    if (running) return
    setMode(nextMode)
    resetImport()
  }

  const chooseFile = async (file: File | null) => {
    if (!file) return
    setError('')
    try {
      const existing = mode === 'edit' ? await ensureExistingProperties() : []
      const loaded = await readPropertyWorkbook(file)
      const preferred =
        loaded.sheets.find((sheet) => sheet.name.trim().toLowerCase() === 'properties') ??
        loaded.sheets[0]
      setWorkbook(loaded)
      setSheetName(preferred.name)
      applySheet(loaded, preferred.name, mode, existing)
    } catch (loadError) {
      setError(presentError(loadError, 'form-submit').message)
      setRows([])
      setWorkbook(null)
    }
  }

  const chooseSheet = async (nextSheet: string) => {
    if (!workbook) return
    const existing = mode === 'edit' ? await ensureExistingProperties() : []
    setSheetName(nextSheet)
    applySheet(workbook, nextSheet, mode, existing)
  }

  const updateRow = (key: string, patch: Partial<PropertyDataRow>) => {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)))
  }

  const submitRows = async (source: PropertyDataRow[]) => {
    if (!source.length) {
      setError('Select at least one valid row first.')
      return
    }

    setRunning(true)
    setError('')

    await runWithConcurrency(source, PROPERTY_DATA_CONCURRENCY, async (row) => {
      updateRow(row.key, { status: 'submitting', error: '' })
      try {
        const result =
          mode === 'create'
            ? await realEstateApi.createProperty(estateId, row.input!)
            : await realEstateApi.updatePropertyFields(estateId, row.propertyId!, row.patch)
        updateRow(row.key, {
          status: 'success',
          selected: false,
          resultPropertyId: result.id,
          error: '',
        })
      } catch (submitError) {
        updateRow(row.key, {
          status: 'failed',
          selected: true,
          error: presentError(submitError, 'form-submit').message,
        })
      }
    })

    setRunning(false)
    setExistingProperties(null)
    await onChanged()
  }

  const submitSelected = async () => {
    const selected = rows.filter(
      (row) => row.selected && (row.status === 'ready' || row.status === 'failed'),
    )
    await submitRows(selected)
  }

  const retryFailed = async () => {
    const failed = rows.filter((row) => row.status === 'failed')
    await submitRows(failed)
  }

  const downloadCurrent = async (format: 'csv' | 'xlsx') => {
    try {
      const existing = await ensureExistingProperties()
      await downloadEstatePropertyData(estateName, existing, format)
    } catch (downloadError) {
      setError(presentError(downloadError, 'background-action').message)
    }
  }

  const discardInvalid = () => {
    setRows((current) => current.filter((row) => row.status !== 'invalid'))
  }

  return (
    <div
      className="commercial-modal-backdrop"
      role="presentation"
      onMouseDown={() => {
        if (!running) onClose()
      }}
    >
      <section
        className="commercial-modal commercial-modal--xl specialized-real-estate-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Property Data Studio"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="commercial-modal-header">
          <div>
            <h2>Property Data Studio</h2>
            <p>
              {estateName} · Create or edit Estate properties from CSV / Excel without uploading
              spreadsheet files to the backend.
            </p>
          </div>
          <button
            type="button"
            className="commercial-modal-close"
            disabled={running}
            onClick={onClose}
            aria-label="Close"
          >
            <IconX size={16} />
          </button>
        </header>

        <div className="commercial-modal-body specialized-data-studio">
          {error ? <div className="commercial-notice commercial-notice-red">{error}</div> : null}

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>1. Choose workflow</h3>
                <p>
                  Create new inventory or update existing properties by Property ID. Spreadsheet
                  parsing happens entirely in this browser.
                </p>
              </div>
            </div>
            <div className="specialized-data-studio-mode">
              <button
                type="button"
                className={mode === 'create' ? 'is-active' : ''}
                disabled={!canCreate || running}
                onClick={() => changeMode('create')}
              >
                Create properties
              </button>
              <button
                type="button"
                className={mode === 'edit' ? 'is-active' : ''}
                disabled={!canUpdate || running}
                onClick={() => changeMode('edit')}
              >
                Edit existing properties
              </button>
            </div>
          </section>

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>2. Start with a clean template</h3>
                <p>
                  CSV and Excel templates use the same columns. Excel also includes an Instructions
                  sheet.
                </p>
              </div>
            </div>
            <div className="specialized-data-studio-actions">
              <button
                type="button"
                className="specialized-btn"
                disabled={running}
                onClick={() => void downloadPropertyTemplate(mode, 'csv')}
              >
                <IconDownload size={14} />
                CSV template
              </button>
              <button
                type="button"
                className="specialized-btn"
                disabled={running}
                onClick={() => void downloadPropertyTemplate(mode, 'xlsx')}
              >
                <IconFileSpreadsheet size={14} />
                Excel template
              </button>
              {mode === 'edit' ? (
                <>
                  <button
                    type="button"
                    className="specialized-btn"
                    disabled={running || loadingExisting}
                    onClick={() => void downloadCurrent('csv')}
                  >
                    <IconDownload size={14} />
                    Current Estate CSV
                  </button>
                  <button
                    type="button"
                    className="specialized-btn specialized-btn-primary"
                    disabled={running || loadingExisting}
                    onClick={() => void downloadCurrent('xlsx')}
                  >
                    <IconFileSpreadsheet size={14} />
                    Current Estate Excel
                  </button>
                </>
              ) : null}
            </div>
            {mode === 'edit' ? (
              <div className="commercial-notice">
                Recommended: download the current Estate inventory, edit only the cells you want to
                change, then upload it. Blank edit cells mean “no change”.
              </div>
            ) : null}
          </section>

          <section className="commercial-form-section">
            <div className="commercial-form-section-heading">
              <div>
                <h3>3. Upload and validate</h3>
                <p>
                  Invalid rows never block valid rows. You can submit any valid subset and discard
                  the rest.
                </p>
              </div>
            </div>
            <label className="commercial-upload-dropzone specialized-data-studio-upload">
              <div className="commercial-upload-dropzone-icon">
                <IconUpload size={18} />
              </div>
              <div>
                <strong>{workbook ? workbook.filename : 'Choose CSV or Excel file'}</strong>
                <small>CSV, XLSX or XLS · maximum 10 MB · maximum 500 data rows per session</small>
              </div>
              <input
                type="file"
                accept=".csv,.xlsx,.xls,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                disabled={running}
                onChange={(event) => {
                  void chooseFile(event.target.files?.[0] ?? null)
                  event.target.value = ''
                }}
              />
            </label>

            {workbook && workbook.sheets.length > 1 ? (
              <label className="commercial-field">
                <span>Worksheet</span>
                <select
                  value={sheetName}
                  disabled={running}
                  onChange={(event) => void chooseSheet(event.target.value)}
                >
                  {workbook.sheets.map((sheet) => (
                    <option key={sheet.name} value={sheet.name}>
                      {sheet.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            {warnings.map((warning) => (
              <div key={warning} className="commercial-notice">
                {warning}
              </div>
            ))}
            {fileErrors.map((fileError) => (
              <div key={fileError} className="commercial-notice commercial-notice-red">
                {fileError}
              </div>
            ))}
          </section>

          {rows.length ? (
            <section className="commercial-form-section">
              <div className="commercial-form-section-heading">
                <div>
                  <h3>4. Review rows</h3>
                  <p>
                    Check parsed values and edit diffs before applying anything to {estateName}.
                  </p>
                </div>
              </div>

              <div className="specialized-data-studio-summary">
                <article>
                  <span>Total</span>
                  <strong>{summary.total}</strong>
                </article>
                <article>
                  <span>Ready</span>
                  <strong>{summary.ready}</strong>
                </article>
                <article>
                  <span>Needs attention</span>
                  <strong>{summary.invalid}</strong>
                </article>
                {mode === 'edit' ? (
                  <article>
                    <span>No changes</span>
                    <strong>{summary.skipped}</strong>
                  </article>
                ) : null}
                <article>
                  <span>Completed</span>
                  <strong>{summary.success}</strong>
                </article>
                <article>
                  <span>Failed</span>
                  <strong>{summary.failed}</strong>
                </article>
              </div>

              <div className="specialized-data-studio-filter">
                {(['all', 'ready', 'issues'] as RowFilter[]).map((value) => (
                  <button
                    key={value}
                    type="button"
                    className={filter === value ? 'is-active' : ''}
                    onClick={() => setFilter(value)}
                  >
                    {value === 'all' ? 'All' : value === 'ready' ? 'Ready / processed' : 'Issues'}
                  </button>
                ))}
                {summary.invalid ? (
                  <button type="button" onClick={discardInvalid}>
                    Discard invalid rows
                  </button>
                ) : null}
              </div>

              <div className="specialized-table-wrap specialized-data-studio-table-wrap">
                <table className="specialized-table specialized-data-studio-table">
                  <thead>
                    <tr>
                      <th />
                      <th>Row</th>
                      <th>Property</th>
                      <th>Type</th>
                      <th>{mode === 'edit' ? 'Changes' : 'Parsed details'}</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleRows.map((row) => (
                      <tr key={row.key}>
                        <td>
                          <input
                            type="checkbox"
                            aria-label={`Select row ${row.rowNumber}`}
                            disabled={running || !['ready', 'failed'].includes(row.status)}
                            checked={row.selected}
                            onChange={(event) =>
                              updateRow(row.key, { selected: event.target.checked })
                            }
                          />
                        </td>
                        <td>{row.rowNumber}</td>
                        <td>
                          <b>{row.propertyName || `Property ${row.propertyId ?? ''}`}</b>
                          {row.propertyId != null ? <small>ID {row.propertyId}</small> : null}
                        </td>
                        <td>{row.propertyType ?? '—'}</td>
                        <td>
                          {mode === 'edit' ? (
                            row.diffs.length ? (
                              <div className="specialized-data-studio-diffs">
                                {row.diffs.map((diff) => (
                                  <span key={diff.field}>
                                    <b>{diff.label}</b>
                                    <small>
                                      {diff.before} → {diff.after}
                                    </small>
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <small>No changes</small>
                            )
                          ) : (
                            <div className="specialized-data-studio-diffs">
                              <span>
                                <b>Price</b>
                                <small>{row.input?.price ?? 'Estate default'}</small>
                              </span>
                              {row.input?.propertyType === 'plot' ? (
                                <span>
                                  <b>Plot size</b>
                                  <small>
                                    {row.input.plotSize ?? '—'} {row.input.plotSizeUnit ?? 'sqm'}
                                  </small>
                                </span>
                              ) : null}
                            </div>
                          )}

                          {row.errors.length ? (
                            <ul className="specialized-data-studio-errors">
                              {row.errors.map((rowError) => (
                                <li key={rowError}>{rowError}</li>
                              ))}
                            </ul>
                          ) : null}
                          {row.warnings.length ? (
                            <ul className="specialized-data-studio-warnings">
                              {row.warnings.map((warning) => (
                                <li key={warning}>{warning}</li>
                              ))}
                            </ul>
                          ) : null}
                          {row.error ? (
                            <div className="specialized-data-studio-errors">{row.error}</div>
                          ) : null}
                        </td>
                        <td>
                          <span className={`specialized-data-studio-status is-${row.status}`}>
                            {row.status.replace('_', ' ')}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}
        </div>

        <footer className="commercial-modal-footer specialized-data-studio-footer">
          {rows.some((row) => row.status === 'failed') ? (
            <>
              <button
                type="button"
                className="commercial-btn"
                disabled={running}
                onClick={() => void retryFailed()}
              >
                <IconRefresh size={14} />
                Retry failed
              </button>
              <button
                type="button"
                className="commercial-btn"
                disabled={running}
                onClick={() => downloadPropertyResults(mode, rows, true)}
              >
                Download failed rows
              </button>
            </>
          ) : null}
          {rows.some((row) => row.status === 'success' || row.status === 'failed') ? (
            <button
              type="button"
              className="commercial-btn"
              disabled={running}
              onClick={() => downloadPropertyResults(mode, rows, false)}
            >
              Download results
            </button>
          ) : null}
          {workbook ? (
            <button
              type="button"
              className="commercial-btn"
              disabled={running}
              onClick={resetImport}
            >
              Clear file
            </button>
          ) : null}
          <button type="button" className="commercial-btn" disabled={running} onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="commercial-btn commercial-btn-primary"
            disabled={running || summary.selected === 0 || fileErrors.length > 0}
            onClick={() => void submitSelected()}
          >
            {running
              ? 'Applying…'
              : mode === 'create'
                ? `Create selected ${summary.selected}`
                : `Apply selected ${summary.selected}`}
          </button>
        </footer>
      </section>
    </div>
  )
}
