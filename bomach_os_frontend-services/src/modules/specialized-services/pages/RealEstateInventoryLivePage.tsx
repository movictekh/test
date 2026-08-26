import {
  IconArrowLeft,
  IconBuilding,
  IconChevronRight,
  IconExternalLink,
  IconX,
  IconFilePlus,
  IconHome,
  IconMap2,
  IconMapPin2,
  IconPlus,
  IconRefresh,
  IconSearch,
  IconTrash,
  IconWorldWww,
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
import { Tabs, TabsList, TabsTrigger } from '@/shared/ui/tabs'
import {
  CompactActionButton,
  CompactPageToolbar,
  ModulePageFrame,
} from '@/shared/ui/module-controls'

import { mapEstateToInput, realEstateApi } from '../real-estate/real-estate.api'
import { boundaryCenter } from '../real-estate/real-estate.boundary'
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

function estateMediaPath(url: string) {
  try {
    return new URL(url, window.location.origin).pathname.toLowerCase()
  } catch {
    return url.toLowerCase()
  }
}

function estateMediaKind(url: string): 'pdf' | 'video' | 'image' | 'embed' {
  const normalized = estateMediaPath(url)
  if (normalized.endsWith('.pdf')) return 'pdf'
  if (/\.(mp4|webm|mov|m4v|ogg)$/i.test(normalized)) return 'video'
  if (/\.(png|jpg|jpeg|webp|gif|svg)$/i.test(normalized)) return 'image'
  return 'embed'
}

function estateLocationEmbedUrl(estate: {
  preciseAddress: string
  cityTown: string
  state: string
  estateName: string
  boundary?: import('../real-estate/real-estate.types').Boundary
}) {
  const center = boundaryCenter(estate.boundary)
  if (center) {
    return `https://www.google.com/maps?q=${center.lat},${center.lng}&z=16&t=k&output=embed`
  }
  const query = [estate.preciseAddress, estate.cityTown, estate.state, estate.estateName]
    .map((value) => value.trim())
    .filter(Boolean)
    .join(', ')
  return `https://www.google.com/maps?q=${encodeURIComponent(query)}&z=16&t=k&output=embed`
}

function EstateDirectoryList({
  estates,
  onOpen,
}: {
  estates: Array<{
    id: number
    estateCode: string
    estateName: string
    cityTown: string
    state: string
    estateTypeDisplay: string
    estateStatusDisplay: string
    developerCompanyName: string
    isOurEstate: boolean
  }>
  onOpen: (estateId: number) => void
}) {
  return (
    <div className="specialized-table-wrap specialized-table-wrap--directory">
      <table className="specialized-table specialized-table--directory">
        <thead>
          <tr>
            <th>Estate</th>
            <th>Location</th>
            <th>Type</th>
            <th>Status</th>
            <th>Developer</th>
            <th>Ownership</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {estates.map((estate) => (
            <tr key={estate.id}>
              <td>
                <b>{estate.estateName}</b>
                <small>{estate.estateCode}</small>
              </td>
              <td>
                <b>{estate.cityTown || '—'}</b>
                <small>{estate.state || '—'}</small>
              </td>
              <td>{estate.estateTypeDisplay || '—'}</td>
              <td>{estate.estateStatusDisplay || '—'}</td>
              <td>{estate.developerCompanyName || '—'}</td>
              <td>{estate.isOurEstate ? 'Bomach estate' : 'Third-party estate'}</td>
              <td className="specialized-table-action">
                <button
                  type="button"
                  className="specialized-btn specialized-btn-small"
                  onClick={() => onOpen(estate.id)}
                >
                  Open
                  <IconChevronRight size={12} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function StandalonePropertyDirectoryList({
  properties,
}: {
  properties: Property[]
}) {
  return (
    <div className="specialized-table-wrap specialized-table-wrap--directory">
      <table className="specialized-table specialized-table--directory">
        <thead>
          <tr>
            <th>Property</th>
            <th>Type</th>
            <th>Status</th>
            <th>Client</th>
            <th>Price</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {properties.map((property) => (
            <tr key={property.id}>
              <td>
                <b>{property.propertyName}</b>
                <small>{secondary(property)}</small>
              </td>
              <td>{property.propertyTypeDisplay || property.propertyType}</td>
              <td>{property.statusDisplay || property.status}</td>
              <td>{property.clientName || '—'}</td>
              <td>{formatCurrency(property.price)}</td>
              <td>{new Date(property.createdAt).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
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
  const [estateEditOpen, setEstateEditOpen] = useState(false)
  const [propertiesOpen, setPropertiesOpen] = useState(false)
  const [brokerageOpen, setBrokerageOpen] = useState(false)
  const [propertyEditOpen, setPropertyEditOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [formError, setFormError] = useState('')
  const [estateMediaPreview, setEstateMediaPreview] = useState<{
    title: string
    url: string
    kind: 'pdf' | 'video' | 'image' | 'embed'
  } | null>(null)
  const [estateMediaLoading, setEstateMediaLoading] = useState(false)
  const [inventoryView, setInventoryView] = useState<
    'estates' | 'non-estate-properties' | 'brokerage'
  >('estates')
  const [standalonePropertyType, setStandalonePropertyType] = useState<
    'all' | Property['propertyType']
  >('all')

  const canEstateList = hasPermission(user, PERMISSIONS.estatesList)
  const canEstateView = hasPermission(user, PERMISSIONS.estatesView)
  const canEstateCreate = hasPermission(user, PERMISSIONS.estatesCreate)
  const canEstateUpdate = hasPermission(user, PERMISSIONS.estatesUpdate)
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
  const standalonePropertiesQuery = useQuery({
    ...realEstateQueries.standaloneProperties({
      ...(recordSearch.search ? { search: recordSearch.search } : {}),
      ...(standalonePropertyType !== 'all' ? { propertyType: standalonePropertyType } : {}),
      page: 1,
      limit: 100,
    }),
    enabled: !estateId && inventoryView === 'non-estate-properties' && canPropertyList,
  })
  const brokerageQuery = useQuery({
    ...realEstateQueries.brokerage({
      ...(recordSearch.search ? { search: recordSearch.search } : {}),
      page: 1,
      limit: 100,
    }),
    enabled: canBrokerageList,
  })

  const estates = useMemo(() => estatesQuery.data?.items ?? [], [estatesQuery.data?.items])
  const selectedEstate =
    detailQuery.data ?? estates.find((estate) => estate.id === estateId) ?? null
  const estateLocationUrl = useMemo(
    () =>
      selectedEstate?.preciseAddress
        ? estateLocationEmbedUrl(selectedEstate)
        : null,
    [selectedEstate],
  )
  const properties = propertiesQuery.data?.items ?? []
  const standaloneProperties = standalonePropertiesQuery.data?.items ?? []
  const selectedProperty = properties.find((property) => property.id === propertyId) ?? null
  const estateBrokerageListings = useMemo(
    () =>
      selectedEstate
        ? (brokerageQuery.data?.items ?? []).filter((listing) => listing.estateId === selectedEstate.id)
        : [],
    [brokerageQuery.data?.items, selectedEstate],
  )

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
  const updateEstateMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: CreateEstateInput }) =>
      realEstateApi.updateEstate(id, input),
    onSuccess: async (estate) => {
      queryClient.setQueryData(realEstateKeys.estateDetail(estate.id), estate)
      queryClient.setQueryData(
        realEstateKeys.estateList({
          ...(recordSearch.search ? { search: recordSearch.search } : {}),
          page: 1,
          limit: 100,
        }),
        (current:
          | {
              count: number
              items: Array<(typeof estate) | Record<string, unknown>>
            }
          | undefined) => {
          if (!current) return current
          return {
            ...current,
            items: current.items.map((item) =>
              'id' in item && item.id === estate.id ? estate : item,
            ),
          }
        },
      )
      await invalidateEstate(estate.id)
      setEstateEditOpen(false)
      toast.success(`Estate ${estate.estateCode} updated`)
    },
    onError: (error) =>
      toast.error('Estate could not be updated', {
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
      (Boolean(estateId) &&
        ((canEstateView && (detailQuery.isPending || statsQuery.isPending)) ||
          (canPropertyList && propertiesQuery.isPending))))

  if (initialInventoryLoading) {
    return <SectionLoadingState section="real-estate-inventory" />
  }

  const brokerageList = !canBrokerageList ? (
    <div className="specialized-empty">Brokerage access not granted.</div>
  ) : estateBrokerageListings.length ? (
    estateBrokerageListings.map((listing) => (
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

  const inventoryDirectoryState =
    inventoryView === 'estates' ? (
      !canEstateList ? (
        <EmptyState
          title="Estate access required"
          description="You need estate list access before you can review or open estate inventory records."
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
        <EstateDirectoryList
          estates={estates}
          onOpen={(nextEstateId) =>
            void navigate({
              to: '/app/$section',
              params: { section: 'real-estate-inventory' },
              search: (previous) => ({
                ...withoutSearchKeys(previous, ['property']),
                ...previous,
                estate: String(nextEstateId),
              }),
            })
          }
        />
      )
    ) : inventoryView === 'non-estate-properties' ? (
      !canPropertyList ? (
        <EmptyState
          title="Property access required"
          description="You need property list access before non-estate property records can be reviewed here."
        />
      ) : standalonePropertiesQuery.isError ? (
        <ErrorState
          title="Non-estate Properties could not be loaded"
          description={presentError(standalonePropertiesQuery.error, 'section-load').message}
          onRetry={() => void standalonePropertiesQuery.refetch()}
        />
      ) : recordSearch.search && !standaloneProperties.length ? (
        <EmptyState
          title="No non-estate Properties match this search"
          description="Change the property search or clear it to review other non-estate property records."
        />
      ) : !standaloneProperties.length ? (
        <EmptyState
          title="No non-estate Properties yet"
          description="Standalone property records that are not linked to an estate will appear here."
        />
      ) : (
        <StandalonePropertyDirectoryList properties={standaloneProperties} />
      )
    ) : !canBrokerageList ? (
      <EmptyState
        title="Brokerage access required"
        description="You need brokerage list access before brokerage listings can be reviewed here."
      />
    ) : brokerageQuery.isError ? (
      <ErrorState
        title="Brokerage Listings could not be loaded"
        description={presentError(brokerageQuery.error, 'section-load').message}
        onRetry={() => void brokerageQuery.refetch()}
      />
    ) : recordSearch.search && !brokerageQuery.data?.items.length ? (
      <EmptyState
        title="No Brokerage Listings match this search"
        description="Change the listing search or clear it to review other brokerage records."
      />
    ) : !brokerageQuery.data?.items.length ? (
      <EmptyState
        title="No Brokerage Listings yet"
        description="Add the first brokerage listing to start tracking third-party inventory here."
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
          title={selectedEstate ? selectedEstate.estateName : 'Real Estate Inventory'}
          breadcrumb="Specialized Services / Real Estate"
          secondaryAction={
            selectedEstate ? (
              <CompactActionButton
                onClick={() =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'real-estate-inventory' },
                    search: (previous) => withoutSearchKeys(previous, ['estate', 'property']),
                  })
                }
              >
                <IconArrowLeft size={14} />
                Back to inventory
              </CompactActionButton>
            ) : (
              <CompactActionButton
                disabled={!canCreateServiceRequest}
                locked={!canCreateServiceRequest}
                onClick={() =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'service-requests' },
                    search: { create: 'request' },
                  })
                }
              >
                <IconFilePlus size={14} />
                New Request
              </CompactActionButton>
            )
          }
          primaryAction={
            selectedEstate ? (
              <>
                <CompactActionButton disabled={!canPropertyCreate} onClick={() => setPropertiesOpen(true)}>
                  <IconPlus size={14} />
                  Add Properties
                </CompactActionButton>
                <CompactActionButton
                  disabled={!canBrokerageCreate}
                  onClick={() => setBrokerageOpen(true)}
                >
                  <IconPlus size={14} />
                  Add Brokerage Listing
                </CompactActionButton>
                <CompactActionButton
                  tone="primary"
                  disabled={!canEstateCreate}
                  onClick={() => setEstateOpen(true)}
                >
                  <IconPlus size={14} />
                  Add Estate
                </CompactActionButton>
              </>
            ) : (
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
            )
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
            {selectedEstate ? (
              <div>
                <div className="specialized-card-title">Estate controls</div>
                <div className="specialized-card-subtitle">
                  Search this workspace, refresh the record, or update the estate details.
                </div>
              </div>
            ) : (
              <div>
                <div className="specialized-card-title">Inventory Controls</div>
                <div className="specialized-card-subtitle">
                  Manage estates, brokerage listings and estate property records.
                </div>
              </div>
            )}
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
                    standalonePropertiesQuery.refetch(),
                    brokerageQuery.refetch(),
                  ])
                }}
              >
                <IconRefresh size={14} />
                Refresh
              </button>
              {!selectedEstate ? (
                <>
                  <button
                    type="button"
                    className="specialized-btn"
                    disabled={!canPropertyCreate}
                    onClick={() => setPropertiesOpen(true)}
                  >
                    <IconPlus size={14} />
                    Add Properties
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
                    className="specialized-btn specialized-btn-primary"
                    disabled={!canEstateCreate}
                    onClick={() => setEstateOpen(true)}
                  >
                    <IconPlus size={14} />
                    Add Estate
                  </button>
                </>
              ) : null}
            </div>
          </header>
          <div className="specialized-filter-row">
            {selectedEstate ? (
              <button
                type="button"
                className="specialized-btn"
                disabled={!canEstateUpdate}
                onClick={() => setEstateEditOpen(true)}
              >
                <IconMapPin2 size={14} />
                Edit Estate
              </button>
            ) : null}
            {selectedEstate ? (
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
                <option value="">Back to inventory directory</option>
                {estates.map((estate) => (
                  <option key={estate.id} value={estate.id}>
                    {estate.estateCode} · {estate.estateName} — {estate.cityTown}
                  </option>
                ))}
              </select>
            ) : null}
            <label className="commercial-search">
              <IconSearch size={14} />
              <input
                value={searchDraft}
                onChange={(event) => setSearchDraft(event.target.value)}
                placeholder={
                  selectedEstate
                    ? 'Search Estates'
                    : inventoryView === 'estates'
                      ? 'Search Estates'
                      : inventoryView === 'non-estate-properties'
                        ? 'Search non-estate Properties'
                        : 'Search Brokerage Listings'
                }
              />
            </label>
          </div>
        </section>

        {selectedEstate ? (
          <>
            {selectedEstate.estateMapUrl ||
            selectedEstate.virtualTourUrl ||
            selectedEstate.preciseAddress ? (
              <section className="specialized-card">
                <header className="specialized-card-header">
                  <div>
                    <div className="specialized-card-title">Estate map and virtual tour</div>
                  </div>
                </header>
                <div className="specialized-estate-assets">
                  {selectedEstate.preciseAddress ? (
                    <article className="specialized-estate-asset specialized-estate-asset--compact">
                      <div className="specialized-estate-asset-icon">
                        <IconMapPin2 size={18} />
                      </div>
                      <div className="specialized-estate-asset-body">
                        <strong>Location</strong>
                      </div>
                      <button
                        type="button"
                        className="specialized-btn specialized-btn-small"
                        onClick={() => {
                          setEstateMediaPreview({
                            title: `${selectedEstate.estateName} location`,
                            url: estateLocationUrl ?? estateLocationEmbedUrl(selectedEstate),
                            kind: 'embed',
                          })
                          setEstateMediaLoading(true)
                        }}
                      >
                        <IconExternalLink size={12} />
                        Open location
                      </button>
                    </article>
                  ) : null}

                  {selectedEstate.estateMapUrl ? (
                    <article className="specialized-estate-asset specialized-estate-asset--compact">
                      <div className="specialized-estate-asset-icon">
                        <IconMap2 size={18} />
                      </div>
                      <div className="specialized-estate-asset-body">
                        <strong>Estate map</strong>
                      </div>
                      <button
                        type="button"
                        className="specialized-btn specialized-btn-small"
                        onClick={() => {
                          setEstateMediaPreview({
                            title: 'Estate map',
                            url: selectedEstate.estateMapUrl,
                            kind: estateMediaKind(selectedEstate.estateMapUrl),
                          })
                          setEstateMediaLoading(estateMediaKind(selectedEstate.estateMapUrl) === 'embed')
                        }}
                      >
                        <IconExternalLink size={12} />
                        Open map
                      </button>
                    </article>
                  ) : null}

                  {selectedEstate.virtualTourUrl ? (
                    <article className="specialized-estate-asset specialized-estate-asset--compact">
                      <div className="specialized-estate-asset-icon">
                        <IconWorldWww size={18} />
                      </div>
                      <div className="specialized-estate-asset-body">
                        <strong>Virtual tour</strong>
                      </div>
                      <button
                        type="button"
                        className="specialized-btn specialized-btn-small"
                        onClick={() => {
                          setEstateMediaPreview({
                            title: 'Virtual tour',
                            url: selectedEstate.virtualTourUrl,
                            kind: estateMediaKind(selectedEstate.virtualTourUrl),
                          })
                          setEstateMediaLoading(estateMediaKind(selectedEstate.virtualTourUrl) === 'embed')
                        }}
                      >
                        <IconExternalLink size={12} />
                        Open tour
                      </button>
                    </article>
                  ) : null}
                </div>
              </section>
            ) : null}

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
                        className={
                          property.id === propertyId
                            ? `specialized-property-tile ${statusClass(property.status)} is-selected`
                            : `specialized-property-tile ${statusClass(property.status)}`
                        }
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
                  description="Use Add Properties to add Plots, Residential Buildings or Commercial Buildings."
                />
              )}
            </section>

            {canBrokerageList && estateBrokerageListings.length ? (
                <section className="specialized-card">
                  <header className="specialized-card-header">
                    <div>
                      <div className="specialized-card-title">Brokerage Listings</div>
                      <div className="specialized-card-subtitle">
                        Listings linked to {selectedEstate.estateName}
                      </div>
                    </div>
                  </header>
                  {brokerageList}
                </section>
            ) : null}
          </>
        ) : (
          <section className="specialized-card">
            <header className="specialized-card-header">
              <div>
                <div className="specialized-card-title">Inventory Directory</div>
                <div className="specialized-card-subtitle">
                  Switch between estate records and standalone properties, then open the record you want to manage.
                </div>
              </div>
            </header>
            <Tabs
              value={inventoryView}
              onValueChange={(value) =>
                setInventoryView(
                  value === 'brokerage'
                    ? 'brokerage'
                    : value === 'non-estate-properties'
                      ? 'non-estate-properties'
                      : 'estates',
                )
              }
              className="specialized-directory-tabs"
            >
              <TabsList className="specialized-directory-tabs-list">
                <TabsTrigger value="estates">Estates</TabsTrigger>
                <TabsTrigger value="non-estate-properties">Non-estate Properties</TabsTrigger>
                <TabsTrigger value="brokerage">Brokerage Listings</TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="specialized-filter-row specialized-filter-row--directory">
              {inventoryView === 'non-estate-properties' ? (
                <select
                  value={standalonePropertyType}
                  onChange={(event) =>
                    setStandalonePropertyType(
                      event.target.value as 'all' | Property['propertyType'],
                    )
                  }
                >
                  <option value="all">All property types</option>
                  <option value="plot">Plots</option>
                  <option value="residential">Residential</option>
                  <option value="commercial">Commercial</option>
                </select>
              ) : null}
            </div>
            {inventoryDirectoryState}
          </section>
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
      {estateEditOpen && selectedEstate ? (
        <Suspense fallback={<RealEstateWorkspaceFallback />}>
          <CreateEstateLiveWorkspace
            mode="edit"
            saving={updateEstateMutation.isPending}
            initialValue={mapEstateToInput(selectedEstate)}
            onClose={() => setEstateEditOpen(false)}
            onSubmit={(input) =>
              updateEstateMutation.mutate({ id: selectedEstate.id, input })
            }
          />
        </Suspense>
      ) : null}
      {propertiesOpen && selectedEstate ? (
        <BatchCreatePropertiesWorkspace
          estateId={selectedEstate.id}
          estateName={selectedEstate.estateName}
          estates={estates.map((estate) => ({
            id: estate.id,
            estateName: estate.estateName,
            estateCode: estate.estateCode,
          }))}
          onClose={() => setPropertiesOpen(false)}
          onChanged={async () => {
            await invalidateEstate(selectedEstate.id)
          }}
        />
      ) : propertiesOpen ? (
        <BatchCreatePropertiesWorkspace
          estateId={null}
          estateName={null}
          estates={estates.map((estate) => ({
            id: estate.id,
            estateName: estate.estateName,
            estateCode: estate.estateCode,
          }))}
          onClose={() => setPropertiesOpen(false)}
          onChanged={async () => {
            await Promise.all([
              queryClient.invalidateQueries({ queryKey: realEstateKeys.estates() }),
              queryClient.invalidateQueries({ queryKey: realEstateKeys.standaloneProperties() }),
            ])
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
      {selectedProperty && selectedEstate ? (
        <div
          className="commercial-modal-backdrop"
          role="presentation"
          onMouseDown={() =>
            void navigate({
              to: '/app/$section',
              params: { section: 'real-estate-inventory' },
              search: (previous) => withoutSearchKeys(previous, ['property']),
              replace: true,
            })
          }
        >
          <section
            className="commercial-modal specialized-real-estate-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Selected property"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header className="commercial-modal-header">
              <div>
                <h2>Selected Property</h2>
                <p>Inventory record and type-specific details.</p>
              </div>
              <button
                type="button"
                className="commercial-modal-close"
                onClick={() =>
                  void navigate({
                    to: '/app/$section',
                    params: { section: 'real-estate-inventory' },
                    search: (previous) => withoutSearchKeys(previous, ['property']),
                    replace: true,
                  })
                }
                aria-label="Close"
              >
                <IconX size={16} />
              </button>
            </header>
            <div className="commercial-modal-body">
              <SelectedPropertyForm
                key={selectedProperty.id}
                selectedEstateName={selectedEstate.estateName}
                selectedProperty={selectedProperty}
                canPropertyUpdate={canPropertyUpdate}
                canPropertyDelete={canPropertyDelete}
                updatePending={updateMutation.isPending}
                formError={formError}
                setFormError={setFormError}
                onSubmit={(input) => updateMutation.mutate({ id: selectedProperty.id, input })}
                onEdit={() => setPropertyEditOpen(true)}
                onDelete={() => setDeleteId(selectedProperty.id)}
              />
            </div>
          </section>
        </div>
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
      {estateLocationUrl ? (
        <iframe
          title="Estate location preload"
          src={estateLocationUrl}
          aria-hidden="true"
          tabIndex={-1}
          className="specialized-map-preload-frame"
        />
      ) : null}
      {estateMediaPreview ? (
        <div
          className="commercial-modal-backdrop commercial-modal-backdrop--nested"
          role="presentation"
          onMouseDown={() => setEstateMediaPreview(null)}
        >
          <section
            className="commercial-modal commercial-modal--xl specialized-real-estate-modal"
            role="dialog"
            aria-modal="true"
            aria-label={estateMediaPreview.title}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header className="commercial-modal-header">
              <div>
                <h2>{estateMediaPreview.title}</h2>
                <p>Review this file here and open the original file if preview is unavailable.</p>
              </div>
              <button
                type="button"
                className="commercial-modal-close"
                onClick={() => setEstateMediaPreview(null)}
                aria-label="Close"
              >
                <IconX size={16} />
              </button>
            </header>
            <div className="commercial-modal-body">
              <div className="specialized-estate-preview-shell">
                <div className="specialized-estate-preview">
                  {estateMediaLoading ? (
                    <div className="specialized-estate-preview-loading" aria-live="polite">
                      <div className="specialized-estate-spinner" />
                      <span>Loading map…</span>
                    </div>
                  ) : null}
                  {estateMediaPreview.kind === 'pdf' ? (
                    <object
                      aria-label={estateMediaPreview.title}
                      data={`${estateMediaPreview.url}#toolbar=1&navpanes=1&view=FitH`}
                      type="application/pdf"
                      className="specialized-estate-preview-frame"
                    >
                      <div className="specialized-estate-preview-fallback">
                        <strong>Preview unavailable in this popup.</strong>
                        <small>Open the file in a new tab to view the full PDF.</small>
                        <a
                          className="specialized-btn specialized-btn-small"
                          href={estateMediaPreview.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <IconExternalLink size={12} />
                          Open in new tab
                        </a>
                      </div>
                    </object>
                  ) : estateMediaPreview.kind === 'video' ? (
                    <video
                      className="specialized-estate-preview-video"
                      src={estateMediaPreview.url}
                      controls
                      playsInline
                      preload="metadata"
                    />
                  ) : estateMediaPreview.kind === 'image' ? (
                    <img
                      className="specialized-estate-preview-image"
                      src={estateMediaPreview.url}
                      alt={estateMediaPreview.title}
                      onLoad={() => setEstateMediaLoading(false)}
                    />
                  ) : (
                    <iframe
                      title={estateMediaPreview.title}
                      src={estateMediaPreview.url}
                      className="specialized-estate-preview-frame"
                      onLoad={() => setEstateMediaLoading(false)}
                    />
                  )}
                </div>
              </div>
            </div>
            <footer className="commercial-modal-footer">
              <a
                className="commercial-btn"
                href={estateMediaPreview.url}
                target="_blank"
                rel="noreferrer"
              >
                Open original
              </a>
              <button
                type="button"
                className="commercial-btn"
                onClick={() => setEstateMediaPreview(null)}
              >
                Close
              </button>
            </footer>
          </section>
        </div>
      ) : null}
    </ModulePageFrame>
  )
}
