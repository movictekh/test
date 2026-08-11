import { describe,expect,it } from 'vitest'
import { buildPropertyBatch } from '../property-batch'
describe('property batch builder',()=>{
  it('creates deterministic sequential plot templates',()=>{
    const rows=buildPropertyBatch({isOurProperty:true,propertyType:'plot',propertyName:'Plot',price:5000000,status:'available',plotSize:500,plotSizeUnit:'sqm'},3,7,'Plot')
    expect(rows.map(x=>x.input.propertyName)).toEqual(['Plot 07','Plot 08','Plot 09'])
    expect(rows.map(x=>x.input.plotNumber)).toEqual([7,8,9])
  })
})
