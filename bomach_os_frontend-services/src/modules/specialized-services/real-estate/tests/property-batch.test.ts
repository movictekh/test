import { describe, expect, it } from 'vitest'
import { buildPropertyBatch } from '../property-batch'

describe('property batch builder', () => {
  it('creates deterministic sequential plot templates', () => {
    const rows=buildPropertyBatch({isOurProperty:true,propertyType:'plot',propertyName:'Plot',price:5000000,status:'available',plotSize:500,plotSizeUnit:'sqm'},3,7,'Plot')
    expect(rows.map(x=>x.input.propertyName)).toEqual(['Plot 07','Plot 08','Plot 09'])
    expect(rows.map(x=>x.input.plotNumber)).toEqual([7,8,9])
  })
  it('creates residential batches without plot-only fields', () => {
    const rows=buildPropertyBatch({isOurProperty:true,propertyType:'residential',propertyName:'Residence',price:80000000,status:'available',buildingTypeResidential:'duplex',bedrooms:4,bathrooms:4,totalAreaResidential:300},2,1,'Residence')
    expect(rows.map(x=>x.input.propertyName)).toEqual(['Residence 1','Residence 2'])
    expect(rows.every(x=>x.input.plotNumber===undefined)).toBe(true)
  })
  it('creates commercial batches without plot-only fields', () => {
    const rows=buildPropertyBatch({isOurProperty:true,propertyType:'commercial',propertyName:'Commercial Unit',price:150000000,status:'available',buildingTypeCommercial:'office',totalAreaCommercial:500,numberOfFloors:3,unitsOffices:12},2,5,'Commercial Unit')
    expect(rows.map(x=>x.input.propertyName)).toEqual(['Commercial Unit 5','Commercial Unit 6'])
    expect(rows.every(x=>x.input.plotNumber===undefined)).toBe(true)
  })
})

