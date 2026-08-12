import {
  IconBuilding,
  IconFilePlus,
  IconHome,
  IconMap2,
  IconPlus,
  IconRefresh,
  IconSearch,
  IconTrash,
} from '@tabler/icons-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'

import { useAuth } from '@/app/auth'
import { SectionLoadingState } from '@/app/loading/SectionLoadingState'
import { canPerformAction, hasPermission, PERMISSIONS } from '@/app/permissions'
import type { AppSectionSearch } from '@/routes/app/$section'
import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import { withOptionalSearchValue, withoutSearchKeys } from '@/shared/navigation/search-state'
import { ErrorState, useToast } from '@/shared/ui'
import { ConfirmDialog } from '@/shared/ui/confirm-dialog'
import { EmptyState } from '@/shared/ui/empty-state'
import {
  CompactActionButton,
  CompactPageToolbar,
  ModulePageFrame,
} from '@/shared/ui/module-controls'

import { realEstateApi } from '../real-estate/real-estate.api'
import { realEstateKeys } from '../real-estate/real-estate.keys'
import { realEstateQueries } from '../real-estate/real-estate.queries'
import {
  propertyStatuses,
  type BrokerageVerificationStatus,
  type CreateBrokerageInput,
  type CreateEstateInput,
  type CreatePropertyInput,
  type Property,
  type PropertyStatus,
  type QuickUpdatePlotInput,
} from '../real-estate/real-estate.types'
import { validateQuickPlotUpdate } from '../real-estate/real-estate.validation'

const BatchCreatePropertiesWorkspace = lazy(() =>
  import('../workspaces/BatchCreatePropertiesWorkspace').then((module) => ({
    default: module.BatchCreatePropertiesWorkspace,
  })),
)

const CreateBrokerageLiveWorkspace = lazy(() =>
  import('../workspaces/CreateBrokerageLiveWorkspace').then((module) => ({
    default: module.CreateBrokerageLiveWorkspace,
  })),
)

const CreateEstateLiveWorkspace = lazy(() =>
  import('../workspaces/CreateEstateLiveWorkspace').then((module) => ({
    default: module.CreateEstateLiveWorkspace,
  })),
)

const EditPropertyLiveWorkspace = lazy(() =>
  import('../workspaces/EditPropertyLiveWorkspace').then((module) => ({
    default: module.EditPropertyLiveWorkspace,
  })),
)

function RealEstateWorkspaceFallback() {
  return (
    <div className="commercial-modal-backdrop" role="presentation">
      <section
        className="commercial-modal specialized-real-estate-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Loading workspace"
      >
        <div className="commercial-modal-body">
          <div className="commercial-notice">Loading workspace…</div>
        </div>
      </section>
    </div>
  )
}

import '../../commercial/styles/commercial.css'
import '../styles/specialized-services.css'

function statusClass(status: PropertyStatus) {
  if (status === 'available') return 'av'
  if (status === 'reserved') return 'rs'
  if (status === 'sold') return 'sd'
  return 'hd'
}

function kpiTone(label: string) {
  if (label === 'Sold') return 'sd'
  if (label === 'Reserved') return 'rs'
  if (label === 'Available') return 'av'
  return 'nt'
}
function TypeIcon({ property }: { property: Property }) {
  if (property.propertyType === 'plot') return <IconMap2 size={15} />
  if (property.propertyType === 'residential') return <IconHome size={15} />
  return <IconBuilding size={15} />
}
function secondary(property: Property) {
  if (property.propertyType === 'plot')
    return `${property.plotSize ?? '—'} ${property.plotSizeUnit || 'sqm'}`
  if (property.propertyType === 'residential')
    return `${property.buildingTypeResidentialDisplay || property.buildingTypeResidential || 'Residential'} · ${property.bedrooms ?? '—'} bed · ${property.bathrooms ?? '—'} bath`
  return `${property.buildingTypeCommercialDisplay || property.buildingTypeCommercial || 'Commercial'} · ${property.numberOfFloors ?? '—'} floor(s) · ${property.unitsOffices ?? '—'} unit(s)`
}

function SelectedPropertyForm({
  selectedEstateName,
  selectedProperty,
  canPropertyUpdate,
  canPropertyDelete,
  updatePending,
  formError,
  setFormError,
  onSubmit,
  onDelete,
  onEdit,
}: {
  selectedEstateName: string
  selectedProperty: Property
  canPropertyUpdate: boolean
  canPropertyDelete: boolean
  updatePending: boolean
  formError: string
  setFormError: (value: string) => void
  onSubmit: (input: QuickUpdatePlotInput) => void
  onDelete: () => void
  onEdit: () => void
}) {
  const [propertyStatusDraft, setPropertyStatusDraft] = useState<PropertyStatus>(
    selectedProperty.status,
  )
  const needsClientName = propertyStatusDraft === 'reserved' || propertyStatusDraft === 'sold'

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        const d = new FormData(event.currentTarget)
        const statusValue = d.get('status')
        const clientValue = d.get('clientName')
        const priceValue = d.get('price')
        const input: QuickUpdatePlotInput = {
          status: (typeof statusValue === 'string'
            ? statusValue
            : selectedProperty.status) as PropertyStatus,
          clientName:
            typeof clientValue === 'string' ? clientValue.trim() : selectedProperty.clientName,
          price:
            typeof priceValue === 'string' && priceValue !== ''
              ? Number(priceValue)
              : selectedProperty.price,
        }
        const validationError = validateQuickPlotUpdate(input)
        setFormError(validationError)
        if (!validationError) onSubmit(input)
      }}
    >
      <div className="specialized-selected-property">
        <div className="specialized-selected-property-icon">
          <TypeIcon property={selectedProperty} />
        </div>
        <div>
          <strong>{selectedProperty.propertyName}</strong>
          <span>{selectedProperty.propertyTypeDisplay || selectedProperty.propertyType}</span>
          <small>{secondary(selectedProperty)}</small>
        </div>
      </div>
      <div className="specialized-selected-kpi">
        <div>{selectedEstateName}</div>
        <strong>{formatCurrency(selectedProperty.price)}</strong>
        <span>{selectedProperty.statusDisplay || selectedProperty.status}</span>
      </div>
      <label className="specialized-field">
        <span>Status</span>
        <select
          name="status"
          defaultValue={selectedProperty.status}
          disabled={!canPropertyUpdate}
          onChange={(event) => setPropertyStatusDraft(event.target.value as PropertyStatus)}
        >
          {propertyStatuses.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      {needsClientName ? (
        <label className="specialized-field">
          <span>Client / reservation holder</span>
          <input
            name="clientName"
            defaultValue={selectedProperty.clientName}
            disabled={!canPropertyUpdate}
          />
        </label>
      ) : null}
      <label className="specialized-field">
        <span>Agreed price</span>
        <input
          name="price"
          type="number"
          defaultValue={selectedProperty.price}
          disabled={!canPropertyUpdate}
        />
      </label>
      {formError ? (
        <div className="commercial-notice commercial-notice-red">{formError}</div>
      ) : null}
      <button
        className="specialized-btn specialized-btn-primary specialized-btn-block"
        disabled={!canPropertyUpdate || updatePending}
      >
        Save Property Inventory
      </button>
      <button
        type="button"
        className="specialized-btn specialized-btn-block"
        disabled={!canPropertyUpdate}
        onClick={onEdit}
      >
        Edit Property Details
      </button>
      {canPropertyDelete ? (
        <button type="button" className="specialized-btn specialized-btn-block" onClick={onDelete}>
          <IconTrash size={13} />
          Delete Property
        </button>
      ) : null}
    </form>
  )
}

export function RealEstateInventoryLivePage({ recordSearch }: { recordSearch: AppSectionSearch }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const estateId = recordSearch.estate ? Number(recordSearch.estate) : null
  const propertyId = recordSearch.property ? Number(recordSearch.property) : null

  const [searchDraft, setSearchDraft] = useState(recordSearch.search ?? '')
  const [syncedSearch, setSyncedSearch] = useState(recordSearch.search ?? '')
  const [estateOpen, setEstateOpen] = useState(false)
  const [propertiesOpen, setPropertiesOpen] = useState(false)
  const [brokerageOpen, setBrokerageOpen] = useState(false)
  const [propertyEditOpen, setPropertyEditOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [formError, setFormError] = useState('')

  const canEstateList = hasPermission(user, PERMISSIONS.estatesList)
  const canEstateView = hasPermission(user, PERMISSIONS.estatesView)
  const canEstateCreate = hasPermission(user, PERMISSIONS.estatesCreate)
  const canPropertyList = hasPermission(user, PERMISSIONS.propertiesList)
  const canPropertyCreate = hasPermission(user, PERMISSIONS.propertiesCreate)
  const canPropertyUpdate = hasPermission(user, PERMISSIONS.propertiesUpdate)
  const canPropertyDelete = hasPermission(user, PERMISSIONS.propertiesDelete)
  const canBrokerageList = hasPermission(user, PERMISSIONS.brokerageList)
  const canBrokerageCreate = hasPermission(user, PERMISSIONS.brokerageCreate)
  const canBrokerageUpdate = hasPermission(user, PERMISSIONS.brokerageUpdate)
  const canBrokerageDelete = hasPermission(user, PERMISSIONS.brokerageDelete)
  const canCreateServiceRequest = canPerformAction(user, 'requestCreate')
  const canCreateService = canPerformAction(user, 'serviceCreate')

  const estatesQuery = useQuery({
    ...realEstateQueries.estates({
      ...(recordSearch.search ? { search: recordSearch.search } : {}),
      page: 1,
      limit: 100,
    }),
    enabled: canEstateList,
  })
  const detailQuery = useQuery({
    ...realEstateQueries.detail(estateId ?? 0),
    enabled: Boolean(estateId) && canEstateView,
  })
  const statsQuery = useQuery({
    ...realEstateQueries.stats(estateId ?? 0),
    enabled: Boolean(estateId) && canEstateView,
  })
  const propertiesQuery = useQuery({
    ...realEstateQueries.properties(estateId ?? 0, { page: 1, limit: 250 }),
    enabled: Boolean(estateId) && canPropertyList,
  })
  const brokerageQuery = useQuery({
    ...realEstateQueries.brokerage({ page: 1, limit: 8 }),
    enabled: canBrokerageList,
  })
  const brokerageStatsQuery = useQuery({
    ...realEstateQueries.brokerageStats(),
    enabled: canBrokerageList,
  })

  const estates = useMemo(() => estatesQuery.data?.items ?? [], [estatesQuery.data?.items])
  const selectedEstate =
    detailQuery.data ?? estates.find((estate) => estate.id === estateId) ?? null
  const properties = propertiesQuery.data?.items ?? []
  const selectedProperty = properties.find((property) => property.id === propertyId) ?? null

  const setSearchValue = useCallback(
    function <Key extends keyof AppSectionSearch>(
      key: Key,
      value: AppSectionSearch[Key] | '' | null,
    ) {
      void navigate({
        to: '/app/$section',
        params: { section: 'real-estate-inventory' },
        search: (previous) => ({
          ...withoutSearchKeys(previous, [key]),
          ...withOptionalSearchValue<AppSectionSearch, Key>(key, value),
        }),
        replace: true,
      })
    },
    [navigate],
  )

  if ((recordSearch.search ?? '') !== syncedSearch) {
    setSyncedSearch(recordSearch.search ?? '')
    setSearchDraft(recordSearch.search ?? '')
  }
  useEffect(() => {
    if (searchDraft === (recordSearch.search ?? '')) return
    const id = window.setTimeout(() => setSearchValue('search', searchDraft), 350)
    return () => clearTimeout(id)
  }, [recordSearch.search, searchDraft, setSearchValue])
  useEffect(() => {
    if (estateId || !estates[0]) return
    void navigate({
      to: '/app/$section',
      params: { section: 'real-estate-inventory' },
      search: (previous) => ({ ...previous, estate: String(estates[0]!.id) }),
      replace: true,
    })
  }, [estateId, estates, navigate])

  const invalidateEstate = async (id: number) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: realEstateKeys.estates() }),
      queryClient.invalidateQueries({ queryKey: realEstateKeys.estateDetail(id) }),
      queryClient.invalidateQueries({ queryKey: realEstateKeys.estateStats(id) }),
      queryClient.invalidateQueries({ queryKey: realEstateKeys.properties(id) }),
    ])
  }

  const createEstateMutation = useMutation({
    mutationFn: (input: CreateEstateInput) => realEstateApi.createEstate(input),
    onSuccess: async (estate) => {
      await queryClient.invalidateQueries({ queryKey: realEstateKeys.estates() })
      setEstateOpen(false)
      toast.success(`Estate ${estate.estateCode} created`)
      await navigate({
        to: '/app/$section',
        params: { section: 'real-estate-inventory' },
        search: (previous) => ({ ...previous, estate: String(estate.id) }),
      })
      setPropertiesOpen(true)
    },
    onError: (error) =>
      toast.error('Estate could not be created', {
        description: presentError(error, 'form-submit').message,
      }),
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: QuickUpdatePlotInput }) =>
      realEstateApi.quickUpdatePropertyInventory(estateId!, id, input),
    onSuccess: async () => {
      await invalidateEstate(estateId!)
      toast.success('Property inventory updated')
    },
    onError: (error) =>
      toast.error('Property could not be updated', {
        description: presentError(error, 'form-submit').message,
      }),
  })
  const updatePropertyMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: CreatePropertyInput }) =>
      realEstateApi.updateProperty(estateId!, id, input),
    onSuccess: async () => {
      await invalidateEstate(estateId!)
      setPropertyEditOpen(false)
      toast.success('Property details updated')
    },
    onError: (error) =>
      toast.error('Property could not be updated', {
        description: presentError(error, 'form-submit').message,
      }),
  })
  const deleteMutation = useMutation({
    mutationFn: (id: number) => realEstateApi.deleteProperty(estateId!, id),
    onSuccess: async () => {
      setDeleteId(null)
      await invalidateEstate(estateId!)
      toast.success('Property deleted')
      if (propertyId === deleteId)
        await navigate({
          to: '/app/$section',
          params: { section: 'real-estate-inventory' },
          search: (previous) => withoutSearchKeys(previous, ['property']),
          replace: true,
        })
    },
    onError: (error) =>
      toast.error('Property could not be deleted', {
        description: presentError(error, 'background-action').message,
      }),
  })
  const createBrokerageMutation = useMutation({
    mutationFn: (input: CreateBrokerageInput) => realEstateApi.createBrokerage(input),
    onSuccess: async () => {
      setBrokerageOpen(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: realEstateKeys.brokerage() }),
        queryClient.invalidateQueries({ queryKey: realEstateKeys.brokerageStats() }),
      ])
      toast.success('Brokerage listing added')
    },
  })
  const verifyMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: BrokerageVerificationStatus }) =>
      realEstateApi.verifyBrokerage(id, status),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: realEstateKeys.brokerage() }),
        queryClient.invalidateQueries({ queryKey: realEstateKeys.brokerageStats() }),
      ])
      toast.success('Brokerage verification updated')
    },
  })
  const deleteBrokerageMutation = useMutation({
    mutationFn: (id: number) => realEstateApi.deleteBrokerage(id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: realEstateKeys.brokerage() }),
        queryClient.invalidateQueries({ queryKey: realEstateKeys.brokerageStats() }),
      ])
      toast.success('Brokerage listing deleted')
    },
  })

  const initialInventoryLoading =
    canEstateList &&
    (estatesQuery.isPending ||
      (!estateId && Boolean(estatesQuery.data?.items.length)) ||
      (Boolean(estateId) &&
        ((canEstateView && (detailQuery.isPending || statsQuery.isPending)) ||
          (canPropertyList && propertiesQuery.isPending))))

  if (initialInventoryLoading) {
    return <SectionLoadingState section="real-estate-inventory" />
  }

  const brokerageList = !canBrokerageList ? (
    <div className="specialized-empty">Brokerage access not granted.</div>
  ) : brokerageQuery.data?.items.length ? (
    brokerageQuery.data.items.map((listing) => (
      <div key={listing.id} className="specialized-row">
        <div className="specialized-row-main">
          <div className="specialized-row-name">{listing.title}</div>
          <div className="specialized-row-sub">
            {listing.location} · {formatCurrency(listing.price)} ·{' '}
            {listing.verificationStatus.replaceAll('_', ' ')}
          </div>
        </div>
        {canBrokerageUpdate && listing.verificationStatus !== 'verified' ? (
          <button
            type="button"
            className="specialized-btn specialized-btn-small"
            onClick={() => verifyMutation.mutate({ id: listing.id, status: 'verified' })}
          >
            Verify
          </button>
        ) : null}
        {canBrokerageDelete ? (
          <button
            type="button"
            className="specialized-btn specialized-btn-small"
            onClick={() => deleteBrokerageMutation.mutate(listing.id)}
          >
            ×
          </button>
        ) : null}
      </div>
    ))
  ) : (
    <div className="specialized-empty">No Brokerage Listings.</div>
  )

  const estateSelectionState = !canEstateList ? (
    <EmptyState
      title="Estate access required"
      description="You need estate list access before you can select an Estate and manage its property inventory."
    />
  ) : estatesQuery.isError ? (
    <ErrorState
      title="Estates could not be loaded"
      description={presentError(estatesQuery.error, 'section-load').message}
      onRetry={() => void estatesQuery.refetch()}
    />
  ) : recordSearch.search && !estates.length ? (
    <EmptyState
      title="No Estates match this search"
      description="Change the estate search or clear it to review other estate records."
    />
  ) : !estates.length ? (
    <EmptyState
      title="No Estates yet"
      description="Add the first Estate record, then create its property inventory and brokerage links."
      action={
        canEstateCreate ? (
          <button
            type="button"
            className="commercial-btn commercial-btn-primary"
            onClick={() => setEstateOpen(true)}
          >
            Add Estate
          </button>
        ) : null
      }
    />
  ) : (
    <EmptyState
      title="Select an Estate"
      description="Choose an Estate from the selector above to review its property board, details and inventory status."
    />
  )

  const brokerageState = !canBrokerageList ? (
    <EmptyState
      title="Brokerage access required"
      description="You need brokerage list access before third-party listings can be reviewed here."
    />
  ) : brokerageQuery.isError || brokerageStatsQuery.isError ? (
    <ErrorState
      title="Brokerage Listings could not be loaded"
      description={
        presentError(brokerageQuery.error ?? brokerageStatsQuery.error, 'section-load').message
      }
      onRetry={() => {
        void brokerageQuery.refetch()
        void brokerageStatsQuery.refetch()
      }}
    />
  ) : brokerageQuery.isPending || brokerageStatsQuery.isPending ? (
    <EmptyState
      title="Loading Brokerage Listings"
      description="Brokerage listing totals and verification status are being loaded."
    />
  ) : !brokerageQuery.data?.items.length ? (
    <EmptyState
      title="No Brokerage Listings yet"
      description="Add the first third-party property listing to start tracking brokerage inventory here."
      action={
        canBrokerageCreate ? (
          <button
            type="button"
            className="commercial-btn commercial-btn-primary"
            onClick={() => setBrokerageOpen(true)}
          >
            Add Brokerage Listing
          </button>
        ) : null
      }
    />
  ) : (
    brokerageList
  )

  return (
    <ModulePageFrame
      header={
        <CompactPageToolbar
          title="Real Estate Inventory"
          breadcrumb="Specialized Services / Real Estate"
          secondaryAction={
            <CompactActionButton
              disabled={!canCreateServiceRequest}
              locked={!canCreateServiceRequest}
              onClick={() =>
                void navigate({ to: '/app/$section', params: { section: 'service-requests' } })
              }
            >
              <IconFilePlus size={14} />
              New Request
            </CompactActionButton>
          }
          primaryAction={
            <CompactActionButton
              tone="primary"
              disabled={!canCreateService}
              locked={!canCreateService}
              onClick={() =>
                void navigate({ to: '/app/$section', params: { section: 'service-catalogue' } })
              }
            >
              <IconPlus size={14} />
              Create Service
            </CompactActionButton>
          }
        />
      }
    >
      <main className="specialized-content">
        {selectedEstate ? (
          <div className="specialized-kpi-grid">
            {[
              ['Total Properties', statsQuery.data?.total],
              ['Sold', statsQuery.data?.sold],
              ['Reserved', statsQuery.data?.reserved],
              ['Available', statsQuery.data?.available],
            ].map(([label, value]) => (
              <article
                key={String(label)}
                className={`specialized-kpi-card specialized-kpi-card--${kpiTone(String(label))}`}
              >
                <div>{label}</div>
                <strong>{value ?? '—'}</strong>
              </article>
            ))}
          </div>
        ) : null}

        <section className="specialized-card">
          <header className="specialized-card-header specialized-card-header-utility">
            <div>
              <div className="specialized-card-title">Inventory Controls</div>
              <div className="specialized-card-subtitle">
                Manage estates, brokerage listings and estate property records.
              </div>
            </div>
            <div className="specialized-action-row">
              <button
                type="button"
                className="specialized-btn"
                onClick={() => {
                  void Promise.all([
                    estatesQuery.refetch(),
                    detailQuery.refetch(),
                    statsQuery.refetch(),
                    propertiesQuery.refetch(),
                    brokerageQuery.refetch(),
                  ])
                }}
              >
                <IconRefresh size={14} />
                Refresh
              </button>
              <button
                type="button"
                className="specialized-btn"
                disabled={!canBrokerageCreate}
                onClick={() => setBrokerageOpen(true)}
              >
                <IconPlus size={14} />
                Add Brokerage Listing
              </button>
              <button
                type="button"
                className="specialized-btn"
                disabled={!selectedEstate || !canPropertyCreate}
                onClick={() => setPropertiesOpen(true)}
              >
                <IconPlus size={14} />
                Add Estate Properties
              </button>
              <button
                type="button"
                className="specialized-btn specialized-btn-primary"
                disabled={!canEstateCreate}
                onClick={() => setEstateOpen(true)}
              >
                <IconPlus size={14} />
                Add Estate
              </button>
            </div>
          </header>
          <div className="specialized-filter-row">
            <select
              value={estateId ?? ''}
              disabled={!canEstateList}
              onChange={(event) =>
                void navigate({
                  to: '/app/$section',
                  params: { section: 'real-estate-inventory' },
                  search: (previous) => ({
                    ...withoutSearchKeys(previous, ['estate', 'property']),
                    ...(event.target.value ? { estate: event.target.value } : {}),
                  }),
                })
              }
            >
              <option value="">Select Estate</option>
              {estates.map((estate) => (
                <option key={estate.id} value={estate.id}>
                  {estate.estateCode} · {estate.estateName} — {estate.cityTown}
                </option>
              ))}
            </select>
            <label className="commercial-search">
              <IconSearch size={14} />
              <input
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                placeholder="Search Estates"
              />
            </label>
          </div>
        </section>

        {selectedEstate ? (
          <>
            <div className="specialized-grid-2-1">
              <section className="specialized-card">
                <header className="specialized-card-header">
                  <div>
                    <div className="specialized-card-title">Property Inventory</div>
                    <div className="specialized-card-subtitle">
                      All Estate Properties in one board. Color shows status; icon shows Property
                      type.
                    </div>
                  </div>
                  <div className="specialized-inventory-legend">
                    <div className="specialized-legend">
                      <span>
                        <i className="av" />
                        Available
                      </span>
                      <span>
                        <i className="rs" />
                        Reserved
                      </span>
                      <span>
                        <i className="sd" />
                        Sold
                      </span>
                      <span>
                        <i className="hd" />
                        Hold / NFS
                      </span>
                    </div>
                    <div className="specialized-type-legend">
                      <span>
                        <IconMap2 size={13} />
                        Plot
                      </span>
                      <span>
                        <IconHome size={13} />
                        Residential
                      </span>
                      <span>
                        <IconBuilding size={13} />
                        Commercial
                      </span>
                    </div>
                  </div>
                </header>
                {propertiesQuery.isError ? (
                  <ErrorState
                    title="Property Inventory unavailable"
                    description={presentError(propertiesQuery.error, 'section-load').message}
                    onRetry={() => void propertiesQuery.refetch()}
                  />
                ) : properties.length ? (
                  <div className="specialized-property-board-wrap scrollbar-thin">
                    <div className="specialized-property-board">
                      {properties.map((property) => (
                        <button
                          key={property.id}
                          type="button"
                          className={`specialized-property-tile ${statusClass(property.status)}${property.id === propertyId ? 'is-selected' : ''}`}
                          onClick={() =>
                            void navigate({
                              to: '/app/$section',
                              params: { section: 'real-estate-inventory' },
                              search: (previous) => ({
                                ...previous,
                                estate: String(selectedEstate.id),
                                property: String(property.id),
                              }),
                            })
                          }
                        >
                          <span className="specialized-property-tile-icon">
                            <TypeIcon property={property} />
                          </span>
                          <span className="specialized-property-tile-name">
                            {property.propertyName}
                          </span>
                          <span className="specialized-property-tile-type">
                            {property.propertyTypeDisplay || property.propertyType}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <EmptyState
                    title="No Property inventory"
                    description="Use Add Estate Properties to add Plots, Residential Buildings or Commercial Buildings."
                  />
                )}
              </section>

              <aside>
                <section className="specialized-card">
                  <header className="specialized-card-header">
                    <div>
                      <div className="specialized-card-title">Selected Property</div>
                      <div className="specialized-card-subtitle">
                        Inventory record and type-specific details
                      </div>
                    </div>
                  </header>
                  {!selectedProperty ? (
                    <div className="specialized-empty">Select a Property from the board.</div>
                  ) : (
                    <SelectedPropertyForm
                      key={selectedProperty.id}
                      selectedEstateName={selectedEstate.estateName}
                      selectedProperty={selectedProperty}
                      canPropertyUpdate={canPropertyUpdate}
                      canPropertyDelete={canPropertyDelete}
                      updatePending={updateMutation.isPending}
                      formError={formError}
                      setFormError={setFormError}
                      onSubmit={(input) =>
                        updateMutation.mutate({ id: selectedProperty.id, input })
                      }
                      onEdit={() => setPropertyEditOpen(true)}
                      onDelete={() => setDeleteId(selectedProperty.id)}
                    />
                  )}
                </section>

                <section className="specialized-card">
                  <header className="specialized-card-header">
                    <div>
                      <div className="specialized-card-title">Brokerage Listings</div>
                      <div className="specialized-card-subtitle">
                        {brokerageStatsQuery.data?.total ?? 0} total ·{' '}
                        {brokerageStatsQuery.data?.verified ?? 0} verified
                      </div>
                    </div>
                  </header>
                  {brokerageList}
                </section>
              </aside>
            </div>
          </>
        ) : (
          <div className="specialized-grid-2-1">
            <section className="specialized-card">
              <header className="specialized-card-header">
                <div>
                  <div className="specialized-card-title">Estate Inventory</div>
                  <div className="specialized-card-subtitle">
                    Select an estate record before managing its property inventory.
                  </div>
                </div>
              </header>
              {estateSelectionState}
            </section>
            <section className="specialized-card">
              <header className="specialized-card-header">
                <div>
                  <div className="specialized-card-title">Brokerage Listings</div>
                  <div className="specialized-card-subtitle">
                    {brokerageStatsQuery.data?.total ?? 0} total ·{' '}
                    {brokerageStatsQuery.data?.verified ?? 0} verified
                  </div>
                </div>
              </header>
              {brokerageState}
            </section>
          </div>
        )}
      </main>

      {estateOpen ? (
        <Suspense fallback={<RealEstateWorkspaceFallback />}>
          <CreateEstateLiveWorkspace
            saving={createEstateMutation.isPending}

            onClose={() => setEstateOpen(false)}

            onSubmit={(input) => createEstateMutation.mutate(input)}
          />
        </Suspense>
      ) : null}
      {propertiesOpen && selectedEstate ? (
        <BatchCreatePropertiesWorkspace
          estateId={selectedEstate.id}
          estateName={selectedEstate.estateName}
          onClose={() => setPropertiesOpen(false)}
          onChanged={async () => {
            await invalidateEstate(selectedEstate.id)
          }}
        />
      ) : null}
      {brokerageOpen ? (
        <Suspense fallback={<RealEstateWorkspaceFallback />}>
          <CreateBrokerageLiveWorkspace
            estates={estates}

            saving={createBrokerageMutation.isPending}

            onClose={() => setBrokerageOpen(false)}

            onSubmit={(input) => createBrokerageMutation.mutate(input)}
          />
        </Suspense>
      ) : null}
      {propertyEditOpen && selectedProperty ? (
        <EditPropertyLiveWorkspace
          property={selectedProperty}
          saving={updatePropertyMutation.isPending}
          onClose={() => setPropertyEditOpen(false)}
          onSubmit={(input) => updatePropertyMutation.mutate({ id: selectedProperty.id, input })}
        />
      ) : null}
      <ConfirmDialog
        open={deleteId != null}
        title="Delete Property?"
        description="This permanently removes the Property inventory record."
        confirmLabel="Delete Property"
        tone="danger"
        isConfirming={deleteMutation.isPending}
        onCancel={() => setDeleteId(null)}
        onConfirm={() => {
          if (deleteId != null) void deleteMutation.mutateAsync(deleteId)
        }}
      />
    </ModulePageFrame>
  )
}
