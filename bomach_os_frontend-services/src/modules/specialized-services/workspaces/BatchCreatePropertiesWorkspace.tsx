import { useMemo,useState } from 'react'
import { presentError } from '@/shared/errors'
import { buildPropertyBatch } from '../real-estate/property-batch'
import { propertyStatuses,propertyTypes,type CreatePropertyInput,type PropertyBatchItem,type PropertyType } from '../real-estate/real-estate.types'
import { validateProperty } from '../real-estate/real-estate.validation'
import { realEstateApi } from '../real-estate/real-estate.api'

export function BatchCreatePropertiesWorkspace({estateId,estateName,onClose,onChanged}:{estateId:number;estateName:string;onClose:()=>void;onChanged:()=>Promise<void>|void}) {
  const [propertyType,setPropertyType]=useState<PropertyType>('plot')
  const [count,setCount]=useState(10),[start,setStart]=useState(1),[namePrefix,setNamePrefix]=useState('Plot')
  const [price,setPrice]=useState(5_000_000),[plotSize,setPlotSize]=useState(500),[status,setStatus]=useState<CreatePropertyInput['status']>('available')
  const [description,setDescription]=useState(''),[resType,setResType]=useState('house'),[beds,setBeds]=useState(3),[baths,setBaths]=useState(3),[resArea,setResArea]=useState(200)
  const [comType,setComType]=useState('office'),[comArea,setComArea]=useState(500),[floors,setFloors]=useState(1),[units,setUnits]=useState(1)
  const [items,setItems]=useState<PropertyBatchItem[]>([]),[running,setRunning]=useState(false),[error,setError]=useState('')

  const summary=useMemo(()=>({created:items.filter(x=>x.status==='created').length,failed:items.filter(x=>x.status==='failed').length,pending:items.filter(x=>x.status==='queued'||x.status==='creating').length}),[items])

  const template=():CreatePropertyInput=>({
    isOurProperty:true,propertyType,propertyName:namePrefix||'Property',price,description,status,
    ...(propertyType==='plot'?{plotSize,plotSizeUnit:'sqm'}:{}),
    ...(propertyType==='residential'?{buildingTypeResidential:resType,bedrooms:beds,bathrooms:baths,totalAreaResidential:resArea}:{}),
    ...(propertyType==='commercial'?{buildingTypeCommercial:comType,totalAreaCommercial:comArea,numberOfFloors:floors,unitsOffices:units}:{}),
  })

  const createOne=async(item:PropertyBatchItem)=>{
    setItems(rows=>rows.map(x=>x.key===item.key?{...x,status:'creating',error:''}:x))
    try{
      const created=await realEstateApi.createProperty(estateId,item.input)
      setItems(rows=>rows.map(x=>x.key===item.key?{...x,status:'created',propertyId:created.id,error:''}:x))
      return true
    }catch(e){
      const message=presentError(e,'form-submit').message
      setItems(rows=>rows.map(x=>x.key===item.key?{...x,status:'failed',error:message}:x))
      return false
    }
  }

  const runBatch=async()=>{
    const t=template(),validation=validateProperty(t)
    if(validation){setError(validation);return}
    if(!Number.isInteger(count)||count<1||count>250){setError('Batch size must be between 1 and 250 properties.');return}
    const rows=buildPropertyBatch(t,count,start,namePrefix);setItems(rows);setError('');setRunning(true)
    for(const item of rows) await createOne(item)
    setRunning(false);await onChanged()
  }

  const retry=async(item:PropertyBatchItem)=>{setRunning(true);await createOne(item);setRunning(false);await onChanged()}

  return <div className="specialized-modal-backdrop" onMouseDown={()=>!running&&onClose()}><section className="specialized-modal specialized-modal-xl" onMouseDown={e=>e.stopPropagation()}>
    <header className="specialized-modal-header"><div><h2>Add Properties — {estateName}</h2><p>Create a controlled sequential batch. Every item is tracked independently and failed items can be retried.</p></div><button type="button" disabled={running} onClick={onClose}>×</button></header>
    <div className="specialized-modal-body">
      {error?<div className="commercial-notice commercial-notice-red">{error}</div>:null}
      {items.length===0?<div className="specialized-form-grid">
        <label className="specialized-field"><span>Property type</span><select value={propertyType} onChange={e=>{const v=e.target.value as PropertyType;setPropertyType(v);setNamePrefix(v==='plot'?'Plot':v==='residential'?'House':'Unit')}}>{propertyTypes.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</select></label>
        <label className="specialized-field"><span>How many?</span><input type="number" min={1} max={250} value={count} onChange={e=>setCount(Number(e.target.value))}/></label>
        <label className="specialized-field"><span>Name prefix</span><input value={namePrefix} onChange={e=>setNamePrefix(e.target.value)}/></label>
        <label className="specialized-field"><span>Starting number</span><input type="number" min={1} value={start} onChange={e=>setStart(Number(e.target.value))}/></label>
        <label className="specialized-field"><span>Price per property</span><input type="number" min={1} value={price} onChange={e=>setPrice(Number(e.target.value))}/></label>
        <label className="specialized-field"><span>Initial status</span><select value={status} onChange={e=>setStatus(e.target.value as typeof status)}>{propertyStatuses.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</select></label>
        {propertyType==='plot'?<label className="specialized-field"><span>Plot size (sqm)</span><input type="number" min={1} value={plotSize} onChange={e=>setPlotSize(Number(e.target.value))}/></label>:null}
        {propertyType==='residential'?<>
          <label className="specialized-field"><span>Building type</span><select value={resType} onChange={e=>setResType(e.target.value)}><option value="house">House</option><option value="villa">Villa</option><option value="apartment">Apartment</option><option value="townhouse">Townhouse</option><option value="duplex">Duplex</option><option value="bungalow">Bungalow</option><option value="penthouse">Penthouse</option></select></label>
          <label className="specialized-field"><span>Bedrooms</span><input type="number" min={1} value={beds} onChange={e=>setBeds(Number(e.target.value))}/></label>
          <label className="specialized-field"><span>Bathrooms</span><input type="number" min={1} value={baths} onChange={e=>setBaths(Number(e.target.value))}/></label>
          <label className="specialized-field"><span>Total area</span><input type="number" min={1} value={resArea} onChange={e=>setResArea(Number(e.target.value))}/></label>
        </>:null}
        {propertyType==='commercial'?<>
          <label className="specialized-field"><span>Building type</span><select value={comType} onChange={e=>setComType(e.target.value)}><option value="office">Office</option><option value="retail">Retail Space</option><option value="warehouse">Warehouse</option><option value="shopping_mall">Shopping Mall</option><option value="hotel">Hotel</option><option value="mixed_use">Mixed Use</option></select></label>
          <label className="specialized-field"><span>Total area</span><input type="number" min={1} value={comArea} onChange={e=>setComArea(Number(e.target.value))}/></label>
          <label className="specialized-field"><span>Floors</span><input type="number" min={1} value={floors} onChange={e=>setFloors(Number(e.target.value))}/></label>
          <label className="specialized-field"><span>Units / offices</span><input type="number" min={0} value={units} onChange={e=>setUnits(Number(e.target.value))}/></label>
        </>:null}
        <label className="specialized-field specialized-field-full"><span>Description</span><textarea value={description} onChange={e=>setDescription(e.target.value)}/></label>
      </div>:<>
        <div className="specialized-batch-banner">
          <div><b>{running?'Creating property inventory…':'Batch completed'}</b><span>{summary.created} created · {summary.failed} failed · {summary.pending} pending</span></div>
          <progress value={summary.created+summary.failed} max={items.length}/>
        </div>
        <div className="specialized-batch-list">{items.map(item=><div key={item.key} className={`specialized-batch-row specialized-batch-row--${item.status}`}>
          <div><b>{item.input.propertyName}</b><small>#{item.sequence} · {item.status}{item.propertyId?` · ID ${item.propertyId}`:''}</small>{item.error?<p>{item.error}</p>:null}</div>
          {item.status==='failed'?<button type="button" className="specialized-btn specialized-btn-small" disabled={running} onClick={()=>void retry(item)}>Retry</button>:null}
        </div>)}</div>
      </>}
    </div>
    <footer className="specialized-modal-footer">
      <button type="button" className="specialized-btn" disabled={running} onClick={onClose}>{items.length?'Close':'Cancel'}</button>
      {items.length===0?<button type="button" className="specialized-btn specialized-btn-primary" disabled={running} onClick={()=>void runBatch()}>Create {count} Propert{count===1?'y':'ies'}</button>:null}
    </footer>
  </section></div>
}
