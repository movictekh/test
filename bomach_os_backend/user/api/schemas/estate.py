from ninja import Schema
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class CoordinateSchema(Schema):
    """A single lat/lng coordinate point"""
    lat: Decimal
    lng: Decimal


class EstateCreateSchema(Schema):
    """Schema for creating an estate"""
    is_our_estate: bool = True
    
    legal_fee: Optional[Decimal] = None
    development_fee: Optional[Decimal] = None
    receipt_fee: Optional[Decimal] = None

    estate_name: str
    estate_code: str
    estate_type: str
    developer_company_name: str
    estate_description: str

    # Location
    country: str
    country_code: Optional[str] = None
    state: str
    city_town: str
    precise_address: str
    boundary: Optional[List[CoordinateSchema]] = None

    # Estate Documents (URLs from upload endpoint)
    documents: Optional[List[str]] = None

    # Documents - Title Documents
    has_c_of_o: bool = False
    has_deed_of_assignment: bool = False
    has_survey_plan: bool = False
    zoning_information: Optional[str] = None

    # Government Approvals
    has_planning_permit: bool = False
    has_building_approval: bool = False
    has_environmental_clearance: bool = False

    # Features & Marketing
    price_per_sqm: Decimal
    available_plot_sizes: Optional[str] = None
    min_price_other_properties: Optional[Decimal] = None
    max_price_other_properties: Optional[Decimal] = None
    estate_status: str
    total_area: Optional[Decimal] = None
    area_unit: str = 'sqm'

    # Amenities
    has_roads: bool = False
    has_electricity: bool = False
    has_water: bool = False
    has_fencing: bool = False
    has_security: bool = False
    has_drainage: bool = False
    has_recreation: bool = False

    # Tags
    tags: Optional[List[str]] = None


class EstateUpdateSchema(Schema):
    """Schema for updating an estate"""
    is_our_estate: Optional[bool] = None
    
    legal_fee: Optional[Decimal] = None
    development_fee: Optional[Decimal] = None
    receipt_fee: Optional[Decimal] = None

    estate_name: Optional[str] = None
    estate_type: Optional[str] = None
    developer_company_name: Optional[str] = None
    estate_description: Optional[str] = None

    # Location
    country: Optional[str] = None
    country_code: Optional[str] = None
    state: Optional[str] = None
    city_town: Optional[str] = None
    precise_address: Optional[str] = None
    boundary: Optional[List[CoordinateSchema]] = None

    # Estate Documents
    documents: Optional[List[str]] = None

    # Documents
    has_c_of_o: Optional[bool] = None
    has_deed_of_assignment: Optional[bool] = None
    has_survey_plan: Optional[bool] = None
    zoning_information: Optional[str] = None

    # Government Approvals
    has_planning_permit: Optional[bool] = None
    has_building_approval: Optional[bool] = None
    has_environmental_clearance: Optional[bool] = None

    # Features
    price_per_sqm: Optional[Decimal] = None
    available_plot_sizes: Optional[str] = None
    min_price_other_properties: Optional[Decimal] = None
    max_price_other_properties: Optional[Decimal] = None
    estate_status: Optional[str] = None
    total_area: Optional[Decimal] = None
    area_unit: Optional[str] = None

    # Amenities
    has_roads: Optional[bool] = None
    has_electricity: Optional[bool] = None
    has_water: Optional[bool] = None
    has_fencing: Optional[bool] = None
    has_security: Optional[bool] = None
    has_drainage: Optional[bool] = None
    has_recreation: Optional[bool] = None

    # Tags
    tags: Optional[List[str]] = None

    is_active: Optional[bool] = None


class EstateDocumentSchema(Schema):
    """Schema for estate document response"""
    id: int
    file: str
    caption: str
    created_at: datetime

    @staticmethod
    def resolve_file(obj):
        if obj.file:
            return obj.file.url
        return None


class EstateSchema(Schema):
    """Schema for estate response"""
    id: int
    is_our_estate: bool
    legal_fee: Optional[Decimal] = None
    development_fee: Optional[Decimal] = None
    receipt_fee: Optional[Decimal] = None

    estate_name: str
    estate_code: str
    estate_type: str
    estate_type_display: str
    developer_company_name: str
    estate_description: str

    # Location
    country: str
    country_code: Optional[str] = None
    state: str
    city_town: str
    precise_address: str
    boundary: list = []

    # Estate Documents
    documents: List[EstateDocumentSchema] = []

    # Documents
    has_c_of_o: bool
    has_deed_of_assignment: bool
    has_survey_plan: bool
    zoning_information: str
    title_documents: List[str]

    # Government Approvals
    has_planning_permit: bool
    has_building_approval: bool
    has_environmental_clearance: bool
    government_approvals: List[str]

    # Features
    price_per_sqm: Decimal
    available_plot_sizes: str
    min_price_other_properties: Optional[Decimal] = None
    max_price_other_properties: Optional[Decimal] = None
    estate_status: str
    estate_status_display: str
    total_area: Optional[Decimal] = None
    area_unit: str

    # Amenities
    has_roads: bool
    has_electricity: bool
    has_water: bool
    has_fencing: bool
    has_security: bool
    has_drainage: bool
    has_recreation: bool
    amenities: List[str]

    # Tags
    tags: list

    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_estate_type_display(obj):
        return obj.get_estate_type_display()

    @staticmethod
    def resolve_estate_status_display(obj):
        return obj.get_estate_status_display()

    @staticmethod
    def resolve_documents(obj):
        return list(obj.documents.all())

    @staticmethod
    def resolve_title_documents(obj):
        docs = []
        if obj.has_c_of_o:
            docs.append("C of O")
        if obj.has_deed_of_assignment:
            docs.append("Deed of Assignment")
        if obj.has_survey_plan:
            docs.append("Survey Plan")
        return docs

    @staticmethod
    def resolve_government_approvals(obj):
        approvals = []
        if obj.has_planning_permit:
            approvals.append("Planning Permit")
        if obj.has_building_approval:
            approvals.append("Building Approval")
        if obj.has_environmental_clearance:
            approvals.append("Environmental Clearance")
        return approvals

    @staticmethod
    def resolve_amenities(obj):
        amenities = []
        if obj.has_roads:
            amenities.append("Roads")
        if obj.has_electricity:
            amenities.append("Electricity")
        if obj.has_water:
            amenities.append("Water")
        if obj.has_fencing:
            amenities.append("Fencing")
        if obj.has_security:
            amenities.append("Security")
        if obj.has_drainage:
            amenities.append("Drainage")
        if obj.has_recreation:
            amenities.append("Recreation")
        return amenities


class ChoiceSchema(Schema):
    value: str
    label: str


class EstateChoicesSchema(Schema):
    estate_type: List[ChoiceSchema]
    estate_status: List[ChoiceSchema]
    area_unit: List[ChoiceSchema]


# ============== Property Schemas ==============

class PropertyImageSchema(Schema):
    """Schema for property image response"""
    id: int
    image: str
    caption: str
    created_at: datetime

    @staticmethod
    def resolve_image(obj):
        if obj.image:
            return obj.image.url
        return None


class PropertyCreateSchema(Schema):
    """Schema for creating a property"""
    is_our_property: bool = True
    estate_id: Optional[int] = None
    property_type: str  # 'plot', 'residential', 'commercial'
    property_name: str
    price: Decimal
    boundary: Optional[List[CoordinateSchema]] = None
    description: Optional[str] = None
    status: str = 'available'

    # Plot-specific
    plot_number: Optional[int] = None
    client_name: Optional[str] = None
    plot_size: Optional[Decimal] = None
    plot_size_unit: Optional[str] = 'acres'

    # Residential-specific
    building_type_residential: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floors_residential: Optional[int] = None
    total_area_residential: Optional[Decimal] = None

    # Commercial-specific
    building_type_commercial: Optional[str] = None
    total_area_commercial: Optional[Decimal] = None
    number_of_floors: Optional[int] = None
    units_offices: Optional[int] = None

    images: Optional[List[str]] = None  # URLs from upload endpoint


class PropertyUpdateSchema(Schema):
    """Schema for updating a property"""
    is_our_property: Optional[bool] = None
    property_type: Optional[str] = None
    property_name: Optional[str] = None
    price: Optional[Decimal] = None
    boundary: Optional[List[CoordinateSchema]] = None
    description: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None

    # Plot-specific
    plot_number: Optional[int] = None
    client_name: Optional[str] = None
    plot_size: Optional[Decimal] = None
    plot_size_unit: Optional[str] = None

    # Residential-specific
    building_type_residential: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floors_residential: Optional[int] = None
    total_area_residential: Optional[Decimal] = None

    # Commercial-specific
    building_type_commercial: Optional[str] = None
    total_area_commercial: Optional[Decimal] = None
    number_of_floors: Optional[int] = None
    units_offices: Optional[int] = None

    images: Optional[List[str]] = None  # URLs from upload endpoint


class PropertySchema(Schema):
    """Schema for property response"""
    id: int
    is_our_property: bool
    estate_id: Optional[int] = None
    estate_name: Optional[str] = None
    estate_code: Optional[str] = None

    property_type: str
    property_type_display: str
    property_name: str
    price: Decimal
    boundary: list = []
    description: str
    status: str
    status_display: str

    # Plot-specific
    plot_number: Optional[int] = None
    client_name: Optional[str] = None
    plot_size: Optional[Decimal] = None
    plot_size_unit: Optional[str] = None

    # Residential-specific
    building_type_residential: Optional[str] = None
    building_type_residential_display: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floors_residential: Optional[int] = None
    total_area_residential: Optional[Decimal] = None

    # Commercial-specific
    building_type_commercial: Optional[str] = None
    building_type_commercial_display: Optional[str] = None
    total_area_commercial: Optional[Decimal] = None
    number_of_floors: Optional[int] = None
    units_offices: Optional[int] = None

    images: List[PropertyImageSchema] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_estate_name(obj):
        if obj.estate:
            return obj.estate.estate_name
        return None

    @staticmethod
    def resolve_estate_code(obj):
        if obj.estate:
            return obj.estate.estate_code
        return None

    @staticmethod
    def resolve_property_type_display(obj):
        return obj.get_property_type_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_building_type_residential_display(obj):
        if obj.building_type_residential:
            return obj.get_building_type_residential_display()
        return None

    @staticmethod
    def resolve_building_type_commercial_display(obj):
        if obj.building_type_commercial:
            return obj.get_building_type_commercial_display()
        return None

    @staticmethod
    def resolve_images(obj):
        return list(obj.images.all())


class PropertyChoicesSchema(Schema):
    property_type: List[ChoiceSchema]
    property_status: List[ChoiceSchema]
    residential_building_type: List[ChoiceSchema]
    commercial_building_type: List[ChoiceSchema]
    area_unit: List[ChoiceSchema]


class StandalonePropertyCreateSchema(Schema):
    """Schema for creating a standalone property (no estate)."""
    is_our_property: bool = True
    property_type: str
    property_name: str
    price: Decimal
    boundary: Optional[List[CoordinateSchema]] = None
    description: Optional[str] = None
    status: str = 'available'

    # Plot-specific
    plot_number: Optional[int] = None
    client_name: Optional[str] = None
    plot_size: Optional[Decimal] = None
    plot_size_unit: Optional[str] = 'acres'

    # Residential-specific
    building_type_residential: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floors_residential: Optional[int] = None
    total_area_residential: Optional[Decimal] = None

    # Commercial-specific
    building_type_commercial: Optional[str] = None
    total_area_commercial: Optional[Decimal] = None
    number_of_floors: Optional[int] = None
    units_offices: Optional[int] = None

    images: Optional[List[str]] = None


# Backwards-compatible aliases
PlotImageSchema = PropertyImageSchema
PlotCreateSchema = PropertyCreateSchema
PlotUpdateSchema = PropertyUpdateSchema
PlotSchema = PropertySchema
PlotChoicesSchema = PropertyChoicesSchema


# ============== Estate Stats & Plot Layout ==============

class EstateStatsSchema(Schema):
    """Summary statistics for an estate's properties."""
    total: int
    sold: int
    reserved: int
    available: int
    hold: int
    not_for_sale: int
    total_value: Decimal
    sold_value: Decimal


class PlotLayoutSchema(Schema):
    """Lightweight plot representation for the estate grid view."""
    id: int
    plot_number: Optional[int] = None
    property_name: str
    status: str
    status_display: str
    plot_size: Optional[Decimal] = None
    price: Decimal
    client_name: str = ''


class PlotQuickUpdateSchema(Schema):
    """Rapid status/price/client update for a plot (used by the estate grid)."""
    status: Optional[str] = None
    price: Optional[Decimal] = None
    client_name: Optional[str] = None


# ============== Brokerage Listing Schemas ==============

class BrokerageListingImageSchema(Schema):
    id: int
    image: str
    caption: str
    created_at: datetime

    @staticmethod
    def resolve_image(obj):
        if obj.image:
            return obj.image.url
        return None


class BrokerageListingCreateSchema(Schema):
    """Schema for creating a brokerage listing."""
    title: str
    description: Optional[str] = ''
    location: str
    price: Decimal
    property_type: str
    owner_name: str
    owner_phone: Optional[str] = ''
    owner_email: Optional[str] = ''
    commission_rate: Decimal = Decimal('5.00')
    verification_status: str = 'pending'
    status: str = 'available'
    assigned_agent_id: Optional[int] = None
    estate_id: Optional[int] = None
    tags: Optional[List[str]] = None
    is_active: bool = True
    images: Optional[List[str]] = None  # URLs from upload endpoint


class BrokerageListingUpdateSchema(Schema):
    """Schema for updating a brokerage listing."""
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    price: Optional[Decimal] = None
    property_type: Optional[str] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    commission_rate: Optional[Decimal] = None
    verification_status: Optional[str] = None
    status: Optional[str] = None
    assigned_agent_id: Optional[int] = None
    estate_id: Optional[int] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    images: Optional[List[str]] = None  # URLs from upload endpoint


class BrokerageListingVerifySchema(Schema):
    """Update the verification status of a brokerage listing."""
    verification_status: str


class BrokerageListingSchema(Schema):
    """Schema for brokerage listing response."""
    id: int
    title: str
    description: str
    location: str
    price: Decimal
    property_type: str
    property_type_display: str
    owner_name: str
    owner_phone: str
    owner_email: str
    commission_rate: Decimal
    verification_status: str
    verification_status_display: str
    status: str
    status_display: str
    assigned_agent_id: Optional[int] = None
    assigned_agent_name: Optional[str] = None
    estate_id: Optional[int] = None
    estate_name: Optional[str] = None
    tags: list
    is_active: bool
    images: List[BrokerageListingImageSchema] = []
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_property_type_display(obj):
        return obj.get_property_type_display()

    @staticmethod
    def resolve_verification_status_display(obj):
        return obj.get_verification_status_display()

    @staticmethod
    def resolve_status_display(obj):
        return obj.get_status_display()

    @staticmethod
    def resolve_assigned_agent_id(obj):
        if obj.assigned_agent:
            return obj.assigned_agent.id
        return None

    @staticmethod
    def resolve_assigned_agent_name(obj):
        if obj.assigned_agent:
            return obj.assigned_agent.get_full_name() or str(obj.assigned_agent)
        return None

    @staticmethod
    def resolve_estate_id(obj):
        if obj.estate:
            return obj.estate.id
        return None

    @staticmethod
    def resolve_estate_name(obj):
        if obj.estate:
            return obj.estate.estate_name
        return None

    @staticmethod
    def resolve_images(obj):
        return list(obj.images.all())


class BrokerageStatsSchema(Schema):
    """Summary statistics for brokerage listings."""
    total: int
    verified: int
    pending_verification: int
    inspection_due: int
    sold: int
    available: int
    off_market: int
    total_listing_value: Decimal


class BrokerageChoicesSchema(Schema):
    verification_status: List[ChoiceSchema]
    listing_status: List[ChoiceSchema]
    property_type: List[ChoiceSchema]
