import { IconPlus,IconRefresh,IconSearch,IconTrash } from '@tabler/icons-react'
import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useCallback,useEffect,useMemo,useState } from 'react'
import { useAuth } from '@/app/auth'
import { hasPermission,PERMISSIONS } from '@/app/permissions'
import type { AppSectionSearch } from '@/routes/app/$section'
import { presentError } from '@/shared/errors'
import { formatCurrency } from '@/shared/lib/formatters'
import { withOptionalSearchValue,withoutSearchKeys } from '@/shared/navigation/search-state'
import { ErrorState,useToast } from '@/shared/ui'
import { EmptyState } from '@/shared/ui/empty-state'
import { ConfirmDialog } from '@/shared/ui/confirm-dialog'
import { CompactActionButton,CompactPageToolbar,ModulePageFrame } from '@/shared/ui/module-controls'
import { realEstateApi } from '../real-estate/real-estate.api'
import { realEstateKeys } from '../real-estate/real-estate.keys'
import { realEstateQueries } from '../real-estate/real-estate.queries'
import { propertyStatuses,type CreateEstateInput,type CreateBrokerageInput,type EstatePlotLayoutItem,type PropertyStatus,type QuickUpdatePlotInput,type BrokerageVerificationStatus } from '../real-estate/real-estate.types'
import { validateQuickPlotUpdate } from '../real-estate/real-estate.validation'
import { CreateEstateLiveWorkspace } from '../workspaces/CreateEstateLiveWorkspace'
import { BatchCreatePropertiesWorkspace } from '../workspaces/BatchCreatePropertiesWorkspace'
import { CreateBrokerageLiveWorkspace } from '../workspaces/CreateBrokerageLiveWorkspace'
import '../styles/specialized-services.css'
import '../../commercial/styles/commercial.css'

const plotClass=(s:PropertyStatus)=>s==='available'?'av':s==='reserved'?'rs':s==='sold'?'sd':'hd'
const plotLabel=(p:EstatePlotLayoutItem)=>p.plotNumber!=null?String(p.plotNumber).padStart(2,'0'):p.propertyName

export function RealEstateInventoryLivePage({recordSearch}:{recordSearch:AppSectionSearch}) {
 const {user}=useAuth(),navigate=useNavigate(),qc=useQueryClient(),toast=useToast()
 const estateId=recordSearch.estate?Number(recordSearch.estate):null,plotId=recordSearch.plot?Number(recordSearch.plot):null
 const [searchDraft,setSearchDraft]=useState(recordSearch.search??''),[sync,setSync]=useState(recordSearch.search??'')
 const [createEstate,setCreateEstate]=useState(false),[batch,setBatch]=useState(false),[createBrokerage,setCreateBrokerage]=useState(false)
 const [deletePropertyId,setDeletePropertyId]=useState<number|null>(null)
 const [editStatus,setEditStatus]=useState<PropertyStatus>('available'),[editClient,setEditClient]=useState(''),[editPrice,setEditPrice]=useState(0),[formError,setFormError]=useState('')
 const canEstateList=hasPermission(user,PERMISSIONS.estatesList),canEstateView=hasPermission(user,PERMISSIONS.estatesView),canEstateCreate=hasPermission(user,PERMISSIONS.estatesCreate)
 const canPropertyList=hasPermission(user,PERMISSIONS.propertiesList),canPropertyCreate=hasPermission(user,PERMISSIONS.propertiesCreate),canPropertyUpdate=hasPermission(user,PERMISSIONS.propertiesUpdate),canPropertyDelete=hasPermission(user,PERMISSIONS.propertiesDelete)
 const canBrokerageList=hasPermission(user,PERMISSIONS.brokerageList),canBrokerageCreate=hasPermission(user,PERMISSIONS.brokerageCreate),canBrokerageUpdate=hasPermission(user,PERMISSIONS.brokerageUpdate),canBrokerageDelete=hasPermission(user,PERMISSIONS.brokerageDelete)

 const estates=useQuery({...realEstateQueries.estates({...(recordSearch.search?{search:recordSearch.search}:{}),page:1,limit:100}),enabled:canEstateList})
 const detail=useQuery({...realEstateQueries.detail(estateId??0),enabled:Boolean(estateId)&&canEstateView})
 const stats=useQuery({...realEstateQueries.stats(estateId??0),enabled:Boolean(estateId)&&canEstateView})
 const layout=useQuery({...realEstateQueries.layout(estateId??0),enabled:Boolean(estateId)&&canPropertyList})
 const properties=useQuery({...realEstateQueries.properties(estateId??0,{page:1,limit:100}),enabled:Boolean(estateId)&&canPropertyList})
 const brokerage=useQuery({...realEstateQueries.brokerage({page:1,limit:8}),enabled:canBrokerageList})
 const brokerageStats=useQuery({...realEstateQueries.brokerageStats(),enabled:canBrokerageList})

 const setSearchValue=useCallback(function<Key extends keyof AppSectionSearch>(key:Key,value:AppSectionSearch[Key]|''|null){void navigate({to:'/app/$section',params:{section:'real-estate-inventory'},search:prev=>({...withoutSearchKeys(prev,[key]),...withOptionalSearchValue<AppSectionSearch,Key>(key,value)}),replace:true})},[navigate])
 if((recordSearch.search??'')!==sync){setSync(recordSearch.search??'');setSearchDraft(recordSearch.search??'')}
 useEffect(()=>{if(searchDraft===(recordSearch.search??''))return;const t=window.setTimeout(()=>setSearchValue('search',searchDraft),350);return()=>clearTimeout(t)},[searchDraft,recordSearch.search,setSearchValue])
 const estateOptions=useMemo(()=>estates.data?.items??[],[estates.data?.items])
 useEffect(()=>{if(estateId||!estateOptions[0])return;void navigate({to:'/app/$section',params:{section:'real-estate-inventory'},search:p=>({...p,estate:String(estateOptions[0]!.id)}),replace:true})},[estateId,estateOptions,navigate])
 const selectedEstate=detail.data??estateOptions.find(x=>x.id===estateId)??null
 const selectedPlot=(layout.data??[]).find(x=>x.id===plotId)??null
 useEffect(()=>{if(selectedPlot){setEditStatus(selectedPlot.status);setEditClient(selectedPlot.clientName);setEditPrice(selectedPlot.price);setFormError('')}},[selectedPlot])

 const invalidateEstate=async(id:number)=>Promise.all([
   qc.invalidateQueries({queryKey:realEstateKeys.estates()}),qc.invalidateQueries({queryKey:realEstateKeys.estateDetail(id)}),
   qc.invalidateQueries({queryKey:realEstateKeys.estateStats(id)}),qc.invalidateQueries({queryKey:realEstateKeys.estateLayout(id)}),
   qc.invalidateQueries({queryKey:realEstateKeys.properties(id)}),
 ])
 const createEstateMut=useMutation({mutationFn:(i:CreateEstateInput)=>realEstateApi.createEstate(i),onSuccess:async e=>{await qc.invalidateQueries({queryKey:realEstateKeys.estates()});setCreateEstate(false);toast.success(`Estate ${e.estateCode} created`);await navigate({to:'/app/$section',params:{section:'real-estate-inventory'},search:p=>({...p,estate:String(e.id)})})},onError:e=>toast.error('Estate could not be created',{description:presentError(e,'form-submit').message})})
 const quickMut=useMutation({mutationFn:({id,input}:{id:number;input:QuickUpdatePlotInput})=>realEstateApi.quickUpdatePlot(estateId!,id,input),onSuccess:async p=>{await invalidateEstate(estateId!);toast.success(`${plotLabel(p)} updated`)},onError:e=>toast.error('Plot could not be updated',{description:presentError(e,'form-submit').message})})
 const deletePropMut=useMutation({mutationFn:(id:number)=>realEstateApi.deleteProperty(estateId!,id),onSuccess:async()=>{setDeletePropertyId(null);await invalidateEstate(estateId!);toast.success('Property deleted');if(plotId===deletePropertyId)void navigate({to:'/app/$section',params:{section:'real-estate-inventory'},search:p=>withoutSearchKeys(p,['plot']),replace:true})},onError:e=>toast.error('Property could not be deleted',{description:presentError(e,'background-action').message})})
 const createBrokerageMut=useMutation({mutationFn:(i:CreateBrokerageInput)=>realEstateApi.createBrokerage(i),onSuccess:async()=>{setCreateBrokerage(false);await Promise.all([qc.invalidateQueries({queryKey:realEstateKeys.brokerage()}),qc.invalidateQueries({queryKey:realEstateKeys.brokerageStats()})]);toast.success('Brokerage listing added')},onError:e=>toast.error('Brokerage listing could not be added',{description:presentError(e,'form-submit').message})})
 const verifyMut=useMutation({mutationFn:({id,status}:{id:number;status:BrokerageVerificationStatus})=>realEstateApi.verifyBrokerage(id,status),onSuccess:async()=>{await Promise.all([qc.invalidateQueries({queryKey:realEstateKeys.brokerage()}),qc.invalidateQueries({queryKey:realEstateKeys.brokerageStats()})]);toast.success('Verification updated')}})
 const deleteBrokerageMut=useMutation({mutationFn:(id:number)=>realEstateApi.deleteBrokerage(id),onSuccess:async()=>{await Promise.all([qc.invalidateQueries({queryKey:realEstateKeys.brokerage()}),qc.invalidateQueries({queryKey:realEstateKeys.brokerageStats()})]);toast.success('Brokerage listing deleted')}})

 const refresh=async()=>{await Promise.all([estates.refetch(),...(estateId?[detail.refetch(),stats.refetch(),layout.refetch(),properties.refetch()]:[]),...(canBrokerageList?[brokerage.refetch(),brokerageStats.refetch()]:[])]);toast.success('Real Estate refreshed')}

 return <ModulePageFrame header={<CompactPageToolbar title="Real Estate Inventory" breadcrumb="Specialized Services / Real Estate" secondaryAction={<CompactActionButton onClick={()=>void refresh()}><IconRefresh size={14}/>Refresh</CompactActionButton>} primaryAction={<CompactActionButton tone="primary" disabled={!canEstateCreate} locked={!canEstateCreate} onClick={()=>setCreateEstate(true)}><IconPlus size={14}/>Add Estate</CompactActionButton>}/>}>
  <main className="specialized-content">
   <section className="specialized-card">
    <div className="specialized-filter-row">
     <select value={estateId??''} onChange={e=>void navigate({to:'/app/$section',params:{section:'real-estate-inventory'},search:p=>({...withoutSearchKeys(p,['estate','plot']),...(e.target.value?{estate:e.target.value}:{})})})}><option value="">Select Estate</option>{estateOptions.map(x=><option key={x.id} value={x.id}>{x.estateCode} · {x.estateName} — {x.cityTown}</option>)}</select>
     <label className="commercial-search"><IconSearch size={14}/><input value={searchDraft} onChange={e=>setSearchDraft(e.target.value)} placeholder="Search Estates"/></label>
     <span className="grow"/>
     <button className="specialized-btn" disabled={!canBrokerageCreate} onClick={()=>setCreateBrokerage(true)}>Add Brokerage Property</button>
     <button className="specialized-btn specialized-btn-primary" disabled={!selectedEstate||!canPropertyCreate} onClick={()=>setBatch(true)}>Add Properties</button>
    </div>
   </section>

   {!selectedEstate?<EmptyState title="No Estate selected" description="Create or select an Estate to manage its property inventory."/>:<>
    <div className="specialized-kpi-grid">
     {[['Total plots',stats.data?.total],['Sold plots',stats.data?.sold],['Reserved plots',stats.data?.reserved],['Available plots',stats.data?.available]].map(([l,v])=><article key={String(l)} className="specialized-kpi-card"><div>{l}</div><strong>{v??'—'}</strong></article>)}
    </div>
    <div className="specialized-grid-2-1">
     <section className="specialized-card">
      <header className="specialized-card-header"><div><div className="specialized-card-title">Estate Layout & Inventory</div><div className="specialized-card-subtitle">Click a property to reserve, sell, release, hold or inspect it.</div></div><div className="specialized-legend"><span><i className="av"/>Available</span><span><i className="rs"/>Reserved</span><span><i className="sd"/>Sold</span><span><i className="hd"/>Hold / NFS</span></div></header>
      {layout.isError?<ErrorState title="Layout unavailable" description={presentError(layout.error,'section-load').message} onRetry={()=>void layout.refetch()}/>:layout.data?.length?<div className="specialized-plot-grid">{layout.data.map(p=><button key={p.id} className={`specialized-plot ${plotClass(p.status)}`} onClick={()=>void navigate({to:'/app/$section',params:{section:'real-estate-inventory'},search:s=>({...s,estate:String(selectedEstate.id),plot:String(p.id)})})}>{plotLabel(p)}</button>)}</div>:<EmptyState title="No property inventory" description="Use Add Properties to build this Estate's inventory."/ >}
     </section>
     <aside>
      <section className="specialized-card">
       <header className="specialized-card-header"><div><div className="specialized-card-title">Selected Plot</div></div></header>
       {!selectedPlot?<div className="specialized-empty">Select a property.</div>:<form onSubmit={e=>{e.preventDefault();const input={status:editStatus,clientName:editClient.trim(),price:editPrice};const er=validateQuickPlotUpdate(input);setFormError(er);if(!er)quickMut.mutate({id:selectedPlot.id,input})}}>
        <div className="specialized-selected-kpi"><div>{selectedEstate.estateName}</div><strong>{selectedPlot.propertyName}</strong><span>{selectedPlot.plotSize??'—'} sqm · {formatCurrency(selectedPlot.price)}</span></div>
        {formError?<div className="commercial-notice commercial-notice-red">{formError}</div>:null}
        <label className="specialized-field"><span>Status</span><select value={editStatus} disabled={!canPropertyUpdate} onChange={e=>setEditStatus(e.target.value as PropertyStatus)}>{propertyStatuses.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</select></label>
        <label className="specialized-field"><span>Client / reservation holder</span><input value={editClient} disabled={!canPropertyUpdate} onChange={e=>setEditClient(e.target.value)}/></label>
        <label className="specialized-field"><span>Agreed price</span><input type="number" value={editPrice} disabled={!canPropertyUpdate} onChange={e=>setEditPrice(Number(e.target.value))}/></label>
        <button className="specialized-btn specialized-btn-primary specialized-btn-block" disabled={!canPropertyUpdate||quickMut.isPending}>Save Plot Inventory</button>
        {canPropertyDelete?<button type="button" className="specialized-btn specialized-btn-block" onClick={()=>setDeletePropertyId(selectedPlot.id)}><IconTrash size={13}/>Delete Property</button>:null}
       </form>}
      </section>
      <section className="specialized-card"><header className="specialized-card-header"><div><div className="specialized-card-title">Brokerage Listings</div><div className="specialized-card-subtitle">{brokerageStats.data?.total??0} total · {brokerageStats.data?.verified??0} verified</div></div></header>
       {!canBrokerageList?<div className="specialized-empty">Brokerage access not granted.</div>:brokerage.data?.items.length?brokerage.data.items.map(b=><div key={b.id} className="specialized-row"><div className="specialized-row-main"><div className="specialized-row-name">{b.title}</div><div className="specialized-row-sub">{b.location} · {formatCurrency(b.price)} · {b.verificationStatus.replaceAll('_',' ')}</div></div>{canBrokerageUpdate&&b.verificationStatus!=='verified'?<button className="specialized-btn specialized-btn-small" onClick={()=>verifyMut.mutate({id:b.id,status:'verified'})}>Verify</button>:null}{canBrokerageDelete?<button className="specialized-btn specialized-btn-small" onClick={()=>deleteBrokerageMut.mutate(b.id)}>×</button>:null}</div>):<div className="specialized-empty">No brokerage listings.</div>}
      </section>
     </aside>
    </div>
    <section className="specialized-card"><header className="specialized-card-header"><div><div className="specialized-card-title">Property Register</div><div className="specialized-card-subtitle">{properties.data?.count??0} properties in {selectedEstate.estateName}</div></div></header>
     {properties.data?.items.length?<div className="specialized-table-wrap"><table className="specialized-table"><thead><tr><th>Property</th><th>Type</th><th>Status</th><th>Size</th><th>Price</th><th>Holder</th><th></th></tr></thead><tbody>{properties.data.items.map(p=><tr key={p.id}><td><b>{p.propertyName}</b><small>#{p.id}</small></td><td>{p.propertyTypeDisplay||p.propertyType}</td><td>{p.statusDisplay||p.status}</td><td>{p.plotSize??p.totalAreaResidential??p.totalAreaCommercial??'—'}</td><td>{formatCurrency(p.price)}</td><td>{p.clientName||'—'}</td><td>{canPropertyDelete?<button className="specialized-btn specialized-btn-small" onClick={()=>setDeletePropertyId(p.id)}>Delete</button>:null}</td></tr>)}</tbody></table></div>:<div className="specialized-empty">No property records.</div>}
    </section>
   </>}
  </main>
  {createEstate?<CreateEstateLiveWorkspace saving={createEstateMut.isPending} onClose={()=>setCreateEstate(false)} onSubmit={i=>createEstateMut.mutate(i)}/>:null}
  {batch&&selectedEstate?<BatchCreatePropertiesWorkspace estateId={selectedEstate.id} estateName={selectedEstate.estateName} onClose={()=>setBatch(false)} onChanged={()=>invalidateEstate(selectedEstate.id)}/>:null}
  {createBrokerage?<CreateBrokerageLiveWorkspace estates={estateOptions} saving={createBrokerageMut.isPending} onClose={()=>setCreateBrokerage(false)} onSubmit={i=>createBrokerageMut.mutate(i)}/>:null}
  <ConfirmDialog open={deletePropertyId!=null} title="Delete Property?" description="This permanently removes the Property record. The current backend does not restrict deletion by sale state, so verify that this is appropriate before confirming." confirmLabel="Delete Property" tone="danger" isConfirming={deletePropMut.isPending} onCancel={()=>setDeletePropertyId(null)} onConfirm={()=>deletePropertyId!=null?deletePropMut.mutateAsync(deletePropertyId):Promise.resolve()}/>
 </ModulePageFrame>
}
