import { useState } from 'react'
import { brokerageStatuses,brokerageVerificationStatuses,type CreateBrokerageInput,type Estate } from '../real-estate/real-estate.types'
import { validateBrokerage } from '../real-estate/real-estate.validation'
export function CreateBrokerageLiveWorkspace({estates,saving,onClose,onSubmit}:{estates:Estate[];saving:boolean;onClose:()=>void;onSubmit:(i:CreateBrokerageInput)=>void}) {
 const [v,setV]=useState<CreateBrokerageInput>({title:'',description:'',location:'',price:0,propertyType:'land',ownerName:'',ownerPhone:'',ownerEmail:'',commissionRate:5,verificationStatus:'pending',status:'available',estateId:null,tags:[]}),[tags,setTags]=useState(''),[error,setError]=useState('')
 const set=<K extends keyof CreateBrokerageInput>(k:K,val:CreateBrokerageInput[K])=>setV(x=>({...x,[k]:val}))
 return <div className="specialized-modal-backdrop" onMouseDown={onClose}><form className="specialized-modal" onMouseDown={e=>e.stopPropagation()} onSubmit={e=>{e.preventDefault();const input={...v,tags:tags.split(',').map(x=>x.trim()).filter(Boolean)};const er=validateBrokerage(input);setError(er);if(!er)onSubmit(input)}}>
  <header className="specialized-modal-header"><div><h2>Add Brokerage Property</h2><p>Third-party property managed on commission.</p></div><button type="button" onClick={onClose}>×</button></header>
  <div className="specialized-modal-body specialized-form-grid">
   {error?<div className="commercial-notice commercial-notice-red specialized-field-full">{error}</div>:null}
   <label className="specialized-field"><span>Property title *</span><input value={v.title} onChange={e=>set('title',e.target.value)}/></label>
   <label className="specialized-field"><span>Property type</span><select value={v.propertyType} onChange={e=>set('propertyType',e.target.value as typeof v.propertyType)}><option value="land">Land</option><option value="residential">Residential</option><option value="commercial">Commercial</option></select></label>
   <label className="specialized-field specialized-field-full"><span>Location *</span><input value={v.location} onChange={e=>set('location',e.target.value)}/></label>
   <label className="specialized-field"><span>Asking price *</span><input type="number" min={1} value={v.price} onChange={e=>set('price',Number(e.target.value))}/></label>
   <label className="specialized-field"><span>Commission (%)</span><input type="number" min={0} max={100} value={v.commissionRate} onChange={e=>set('commissionRate',Number(e.target.value))}/></label>
   <label className="specialized-field"><span>Owner / mandate giver *</span><input value={v.ownerName} onChange={e=>set('ownerName',e.target.value)}/></label>
   <label className="specialized-field"><span>Owner phone</span><input value={v.ownerPhone} onChange={e=>set('ownerPhone',e.target.value)}/></label>
   <label className="specialized-field"><span>Owner email</span><input type="email" value={v.ownerEmail} onChange={e=>set('ownerEmail',e.target.value)}/></label>
   <label className="specialized-field"><span>Verification</span><select value={v.verificationStatus} onChange={e=>set('verificationStatus',e.target.value as typeof v.verificationStatus)}>{brokerageVerificationStatuses.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</select></label>
   <label className="specialized-field"><span>Market status</span><select value={v.status} onChange={e=>set('status',e.target.value as typeof v.status)}>{brokerageStatuses.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</select></label>
   <label className="specialized-field"><span>Related Estate</span><select value={v.estateId??0} onChange={e=>set('estateId',Number(e.target.value)||null)}><option value={0}>No Estate link</option>{estates.map(x=><option key={x.id} value={x.id}>{x.estateCode} · {x.estateName}</option>)}</select></label>
   <label className="specialized-field"><span>Tags</span><input value={tags} onChange={e=>setTags(e.target.value)}/></label>
   <label className="specialized-field specialized-field-full"><span>Description</span><textarea value={v.description} onChange={e=>set('description',e.target.value)}/></label>
  </div>
  <footer className="specialized-modal-footer"><button type="button" className="specialized-btn" onClick={onClose}>Cancel</button><button className="specialized-btn specialized-btn-primary" disabled={saving}>{saving?'Adding...':'Add Listing'}</button></footer>
 </form></div>
}
