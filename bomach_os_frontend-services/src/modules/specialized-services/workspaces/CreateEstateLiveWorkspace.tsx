import { useForm } from '@tanstack/react-form'
import { estateStatuses,estateTypes,type CreateEstateInput } from '../real-estate/real-estate.types'
import { validateEstate } from '../real-estate/real-estate.validation'
import { useState } from 'react'
export function CreateEstateLiveWorkspace({saving,onClose,onSubmit}:{saving:boolean;onClose:()=>void;onSubmit:(i:CreateEstateInput)=>void}) {
  const [error,setError]=useState('')
  const form=useForm({defaultValues:{
    isOurEstate:true,estateName:'',estateCode:'',estateType:'residential' as const,developerCompanyName:'Bomach',
    estateDescription:'',country:'Nigeria',countryCode:'NGA',state:'',cityTown:'',preciseAddress:'',
    hasCOfO:false,hasDeedOfAssignment:false,hasSurveyPlan:false,zoningInformation:'',hasPlanningPermit:false,
    hasBuildingApproval:false,hasEnvironmentalClearance:false,pricePerSqm:0,availablePlotSizes:'',
    minPriceOtherProperties:0,maxPriceOtherProperties:0,estateStatus:'available' as const,totalArea:0,areaUnit:'sqm',
    hasRoads:false,hasElectricity:false,hasWater:false,hasFencing:false,hasSecurity:false,hasDrainage:false,hasRecreation:false,
    legalFee:0,developmentFee:0,receiptFee:0,tags:'',
  },onSubmit:({value})=>{
    const input:CreateEstateInput={...value,
      minPriceOtherProperties:value.minPriceOtherProperties||null,maxPriceOtherProperties:value.maxPriceOtherProperties||null,
      totalArea:value.totalArea||null,legalFee:value.legalFee||null,developmentFee:value.developmentFee||null,receiptFee:value.receiptFee||null,
      tags:value.tags.split(',').map(x=>x.trim()).filter(Boolean),
    }
    const e=validateEstate(input);setError(e);if(!e)onSubmit(input)
  }})
  return <div className="specialized-modal-backdrop" onMouseDown={onClose}><form className="specialized-modal specialized-modal-xl" onMouseDown={e=>e.stopPropagation()} onSubmit={e=>{e.preventDefault();void form.handleSubmit()}}>
    <header className="specialized-modal-header"><div><h2>Add Estate</h2><p>Create the canonical Estate record. Plot inventory can be batch-created immediately afterwards.</p></div><button type="button" onClick={onClose}>×</button></header>
    <div className="specialized-modal-body">
      {error?<div className="commercial-notice commercial-notice-red">{error}</div>:null}
      <div className="specialized-form-grid">
        <form.Field name="estateName">{f=><label className="specialized-field"><span>Estate name *</span><input autoFocus value={f.state.value} onChange={e=>f.handleChange(e.target.value)}/></label>}</form.Field>
        <form.Field name="estateCode">{f=><label className="specialized-field"><span>Estate code *</span><input value={f.state.value} onChange={e=>f.handleChange(e.target.value)} placeholder="EST-001"/></label>}</form.Field>
        <form.Field name="estateType">{f=><label className="specialized-field"><span>Estate type</span><select value={f.state.value} onChange={e=>f.handleChange(e.target.value as typeof f.state.value)}>{estateTypes.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</select></label>}</form.Field>
        <form.Field name="estateStatus">{f=><label className="specialized-field"><span>Status</span><select value={f.state.value} onChange={e=>f.handleChange(e.target.value as typeof f.state.value)}>{estateStatuses.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}</select></label>}</form.Field>
        <form.Field name="developerCompanyName">{f=><label className="specialized-field"><span>Developer / company *</span><input value={f.state.value} onChange={e=>f.handleChange(e.target.value)}/></label>}</form.Field>
        <form.Field name="pricePerSqm">{f=><label className="specialized-field"><span>Price / sqm *</span><input type="number" min={0} value={f.state.value} onChange={e=>f.handleChange(Number(e.target.value))}/></label>}</form.Field>
        <form.Field name="estateDescription">{f=><label className="specialized-field specialized-field-full"><span>Description *</span><textarea value={f.state.value} onChange={e=>f.handleChange(e.target.value)}/></label>}</form.Field>
        <form.Field name="country">{f=><label className="specialized-field"><span>Country *</span><input value={f.state.value} onChange={e=>f.handleChange(e.target.value)}/></label>}</form.Field>
        <form.Field name="state">{f=><label className="specialized-field"><span>State *</span><input value={f.state.value} onChange={e=>f.handleChange(e.target.value)}/></label>}</form.Field>
        <form.Field name="cityTown">{f=><label className="specialized-field"><span>City / town *</span><input value={f.state.value} onChange={e=>f.handleChange(e.target.value)}/></label>}</form.Field>
        <form.Field name="preciseAddress">{f=><label className="specialized-field"><span>Precise address *</span><input value={f.state.value} onChange={e=>f.handleChange(e.target.value)}/></label>}</form.Field>
        <form.Field name="availablePlotSizes">{f=><label className="specialized-field"><span>Available plot sizes</span><input value={f.state.value} onChange={e=>f.handleChange(e.target.value)} placeholder="500, 600, 1000"/></label>}</form.Field>
        <form.Field name="totalArea">{f=><label className="specialized-field"><span>Total area</span><input type="number" min={0} value={f.state.value} onChange={e=>f.handleChange(Number(e.target.value))}/></label>}</form.Field>
        <form.Field name="tags">{f=><label className="specialized-field specialized-field-full"><span>Tags</span><input value={f.state.value} onChange={e=>f.handleChange(e.target.value)} placeholder="premium, gated, phase-1"/></label>}</form.Field>
      </div>
      <div className="specialized-check-grid">
        {([
          ['hasCOfO','C of O'],['hasDeedOfAssignment','Deed of Assignment'],['hasSurveyPlan','Survey Plan'],
          ['hasPlanningPermit','Planning Permit'],['hasBuildingApproval','Building Approval'],['hasEnvironmentalClearance','Environmental Clearance'],
          ['hasRoads','Roads'],['hasElectricity','Electricity'],['hasWater','Water'],['hasFencing','Fencing'],['hasSecurity','Security'],['hasDrainage','Drainage'],['hasRecreation','Recreation'],
        ] as const).map(([name,label])=><form.Field key={name} name={name}>{f=><label className="specialized-check"><input type="checkbox" checked={f.state.value} onChange={e=>f.handleChange(e.target.checked)}/><span>{label}</span></label>}</form.Field>)}
      </div>
    </div>
    <footer className="specialized-modal-footer"><button type="button" className="specialized-btn" onClick={onClose}>Cancel</button><button className="specialized-btn specialized-btn-primary" disabled={saving}>{saving?'Creating...':'Create Estate'}</button></footer>
  </form></div>
}
