export interface ApiResponse<TData> {
  data: TData
  message?: string
}

export interface PaginatedResponse<TData> {
  data: TData[]
  meta: {
    page: number
    pageSize: number
    total: number
    totalPages: number
  }
}
