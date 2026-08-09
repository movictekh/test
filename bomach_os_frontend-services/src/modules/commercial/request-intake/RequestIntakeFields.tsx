import { IconRefresh, IconTrash, IconUpload, IconX } from '@tabler/icons-react'

import type { IntakeField } from '../api/service-requests.types'

import { FileTypeIcon } from './file-presentation'
import { formatBytes } from './file-presentation.utils'
import type { PendingUpload } from './request-intake.types'
import { fieldTextValue, nonNegativeNumber } from './request-intake.utils'

export function RequestIntakeFields({
  fields,
  answerValues,
  fieldErrors,
  uploadsByField,
  fieldRefs,
  onValueChange,
  onFileSelection,
  onRetryUpload,
  onRemoveUpload,
}: {
  fields: IntakeField[]
  answerValues: Record<string, unknown>
  fieldErrors: Record<string, string>
  uploadsByField: Record<string, PendingUpload[]>
  fieldRefs: { current: Record<string, HTMLElement | null> }
  onValueChange: (fieldKey: string, value: unknown) => void
  onFileSelection: (field: IntakeField, files: FileList | null) => Promise<void>
  onRetryUpload: (upload: PendingUpload) => void
  onRemoveUpload: (fieldKey: string, uploadId: string) => void
}) {
  return (
    <>
      {fields.map((field) => {
        const value = answerValues[field.key]
        const setValue = (next: unknown) => onValueChange(field.key, next)

        if (field.fieldType === 'textarea') {
          return (
            <label key={field.id} className="commercial-field commercial-field--full">
              <span>
                {field.label}
                {field.required ? ' *' : ''}
              </span>
              <textarea
                ref={(node) => {
                  fieldRefs.current[field.key] = node
                }}
                rows={4}
                placeholder={field.placeholder}
                value={fieldTextValue(value)}
                onChange={(event) => setValue(event.target.value)}
              />
              {fieldErrors[field.key] ? (
                <small className="commercial-field-error">{fieldErrors[field.key]}</small>
              ) : null}
            </label>
          )
        }

        if (field.fieldType === 'select') {
          return (
            <label key={field.id} className="commercial-field">
              <span>
                {field.label}
                {field.required ? ' *' : ''}
              </span>
              <select
                ref={(node) => {
                  fieldRefs.current[field.key] = node
                }}
                value={fieldTextValue(value)}
                onChange={(event) => setValue(event.target.value)}
              >
                <option value="">Select</option>
                {field.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {fieldErrors[field.key] ? (
                <small className="commercial-field-error">{fieldErrors[field.key]}</small>
              ) : null}
            </label>
          )
        }

        if (field.fieldType === 'multiselect') {
          const selected = Array.isArray(value) ? value.map(String) : []
          return (
            <label key={field.id} className="commercial-field">
              <span>
                {field.label}
                {field.required ? ' *' : ''}
              </span>
              <select
                ref={(node) => {
                  fieldRefs.current[field.key] = node
                }}
                multiple
                value={selected}
                onChange={(event) =>
                  setValue(Array.from(event.target.selectedOptions).map((option) => option.value))
                }
              >
                {field.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {fieldErrors[field.key] ? (
                <small className="commercial-field-error">{fieldErrors[field.key]}</small>
              ) : null}
            </label>
          )
        }

        if (field.fieldType === 'checkbox') {
          return (
            <label
              key={field.id}
              className="commercial-check commercial-field--full"
              ref={(node) => {
                fieldRefs.current[field.key] = node
              }}
            >
              <input
                type="checkbox"
                checked={Boolean(value)}
                onChange={(event) => setValue(event.target.checked)}
              />
              <span>
                {field.label}
                {field.required ? ' *' : ''}
              </span>
              {fieldErrors[field.key] ? (
                <small className="commercial-field-error">{fieldErrors[field.key]}</small>
              ) : null}
            </label>
          )
        }

        if (field.fieldType === 'file') {
          const uploads = uploadsByField[field.key] ?? []

          return (
            <div
              key={field.id}
              className="commercial-field commercial-field--full commercial-upload-field"
              ref={(node) => {
                fieldRefs.current[field.key] = node
              }}
            >
              <span>
                {field.label}
                {field.required ? ' *' : ''}
              </span>
              <label className="commercial-upload-dropzone">
                <div className="commercial-upload-dropzone-icon">
                  <IconUpload size={18} />
                </div>
                <div>
                  <strong>Add documents</strong>
                  <small>
                    Upload one or more files now. They will be attached when the request is created.
                  </small>
                </div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => {
                    void onFileSelection(field, event.target.files)
                    event.target.value = ''
                  }}
                />
              </label>

              {uploads.length > 0 ? (
                <div className="commercial-upload-list">
                  {uploads.map((upload) => (
                    <article
                      key={upload.id}
                      className={`commercial-upload-item commercial-upload-item--${upload.status}`}
                    >
                      <div className="commercial-upload-item-icon">
                        <FileTypeIcon fileName={upload.fileName} contentType={upload.contentType} />
                      </div>
                      <div className="commercial-upload-item-body">
                        <div className="commercial-upload-item-top">
                          <strong>{upload.fileName}</strong>
                          <span>{formatBytes(upload.fileSizeBytes)}</span>
                        </div>
                        {upload.status === 'uploading' ? (
                          <div className="commercial-upload-progress">
                            <div className="commercial-upload-progress-bar" />
                          </div>
                        ) : null}
                        {upload.status === 'uploaded' ? (
                          <small>Ready to attach to this request</small>
                        ) : null}
                        {upload.status === 'error' ? <small>{upload.error}</small> : null}
                      </div>
                      <div className="commercial-upload-actions">
                        {upload.status === 'error' ? (
                          <button
                            type="button"
                            className="commercial-upload-remove"
                            onClick={() => onRetryUpload(upload)}
                            aria-label={`Retry ${upload.fileName}`}
                          >
                            <IconRefresh size={14} />
                          </button>
                        ) : null}
                        <button
                          type="button"
                          className="commercial-upload-remove"
                          onClick={() => onRemoveUpload(field.key, upload.id)}
                          aria-label={`Remove ${upload.fileName}`}
                        >
                          {upload.status === 'uploading' ? (
                            <IconX size={14} />
                          ) : (
                            <IconTrash size={14} />
                          )}
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}

              {fieldErrors[field.key] ? (
                <small className="commercial-field-error">{fieldErrors[field.key]}</small>
              ) : null}
            </div>
          )
        }

        return (
          <label key={field.id} className="commercial-field">
            <span>
              {field.label}
              {field.required ? ' *' : ''}
            </span>
            <input
              ref={(node) => {
                fieldRefs.current[field.key] = node
              }}
              type={
                field.fieldType === 'date'
                  ? 'date'
                  : field.fieldType === 'number' || field.fieldType === 'money'
                    ? 'number'
                    : field.fieldType === 'email'
                      ? 'email'
                      : 'text'
              }
              placeholder={field.placeholder}
              value={fieldTextValue(value)}
              onChange={(event) =>
                setValue(
                  field.fieldType === 'number' || field.fieldType === 'money'
                    ? nonNegativeNumber(event.target.value)
                    : event.target.value,
                )
              }
            />
            {fieldErrors[field.key] ? (
              <small className="commercial-field-error">{fieldErrors[field.key]}</small>
            ) : null}
            {field.helpText ? <small>{field.helpText}</small> : null}
          </label>
        )
      })}
    </>
  )
}
