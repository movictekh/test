export type SpecializedServicesSection = 'real-estate-inventory' | 'survey-engineering-others'
export type PlotStatus = 'Available' | 'Reserved' | 'Sold' | 'Hold'
export interface EstatePlot {
  no: string
  status: PlotStatus
  size: number
  client: string
  price: number
}
export interface Estate {
  id: string
  name: string
  location: string
  plots: EstatePlot[]
}
export interface BrokerageProperty {
  id: string
  title: string
  owner: string
  location: string
  price: number
  status: 'Pending Verification' | 'Verified' | 'Inspection Due'
  commissionRate: number
}
export type SpecializedProfileId = 'survey' | 'engineering' | 'logistics' | 'it'
export interface SpecializedServiceProfile {
  id: SpecializedProfileId
  label: string
  title: string
  description: string
  division: string
  stages: string[]
}
export interface SpecializedWorkspace {
  estates: Estate[]
  brokerage: BrokerageProperty[]
  profiles: SpecializedServiceProfile[]
}
export interface CreateEstateInput {
  name: string
  location: string
  plotCount: number
  plotSize: number
  unitPrice: number
}
export interface UpdatePlotInput {
  estateId: string
  plotNo: string
  status: PlotStatus
  client: string
  price: number
}
export interface CreateBrokeragePropertyInput {
  title: string
  owner: string
  location: string
  price: number
  status: BrokerageProperty['status']
  commissionRate: number
}
