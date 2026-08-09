export type UploadStatus = 'uploading' | 'uploaded' | 'error'

export interface PendingUpload {
  id: string
  fieldKey: string
  label: string
  file: File
  fileName: string
  fileSizeBytes: number
  contentType: string
  fileUrl: string
  status: UploadStatus
  error: string
}
