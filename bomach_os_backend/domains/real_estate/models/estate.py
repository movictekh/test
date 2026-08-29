from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models

from user.models.base import BaseModel


class Estate(BaseModel):
    """Model for real estate estates"""

    is_our_estate = models.BooleanField(
        default=True,
        verbose_name="Is Our Estate",
        help_text="Indicates if this estate is developed by our company.",
    )

    ESTATE_TYPE_CHOICES = [
        ("residential", "Residential"),
        ("commercial", "Commercial"),
        ("industrial", "Industrial"),
        ("mixed_use", "Mixed Use"),
        ("land", "Land"),
    ]

    ESTATE_STATUS_CHOICES = [
        ("available", "Available"),
        ("sold_out", "Sold Out"),
        ("under_development", "Under Development"),
        ("coming_soon", "Coming Soon"),
    ]

    AREA_UNIT_CHOICES = [
        ("sqm", "Square Meters"),
        ("hectares", "Hectares"),
        ("acres", "Acres"),
        ("sqft", "Square Feet"),
    ]

    # Basic Information
    estate_name = models.CharField(
        max_length=255,
        verbose_name="Estate Name",
    )
    estate_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Estate Code",
        help_text="Unique code e.g. EST-001",
    )
    estate_type = models.CharField(
        max_length=50,
        choices=ESTATE_TYPE_CHOICES,
        verbose_name="Estate Type",
    )
    developer_company_name = models.CharField(
        max_length=255,
        verbose_name="Developer / Company Name",
    )
    estate_description = models.TextField(
        verbose_name="Estate Description",
    )

    # Location Details
    country = models.CharField(
        max_length=100,
        verbose_name="Country",
        help_text="Country name",
    )
    country_code = models.CharField(
        max_length=3,
        blank=True,
        default="",
        verbose_name="Country Code",
        help_text="ISO 3166-1 alpha-3 code",
    )
    state = models.CharField(
        max_length=100,
        verbose_name="State",
    )
    city_town = models.CharField(
        max_length=100,
        verbose_name="City / Town",
    )
    precise_address = models.TextField(
        verbose_name="Precise Address",
    )
    boundary = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Boundary Coordinates",
        help_text='List of {lat, lng} points defining the estate boundary polygon. e.g. [{"lat": 6.5244, "lng": 3.3792}, ...]',
    )

    # Documents - Title Documents (checkboxes)
    has_c_of_o = models.BooleanField(
        default=False,
        verbose_name="C of O",
    )
    has_deed_of_assignment = models.BooleanField(
        default=False,
        verbose_name="Deed of Assignment",
    )
    has_survey_plan = models.BooleanField(
        default=False,
        verbose_name="Survey Plan",
    )
    zoning_information = models.TextField(
        blank=True,
        default="",
        verbose_name="Zoning Information",
    )

    # Government Approvals (checkboxes)
    has_planning_permit = models.BooleanField(
        default=False,
        verbose_name="Planning Permit",
    )
    has_building_approval = models.BooleanField(
        default=False,
        verbose_name="Building Approval",
    )
    has_environmental_clearance = models.BooleanField(
        default=False,
        verbose_name="Environmental Clearance",
    )

    # Estate Features & Marketing
    price_per_sqm = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Price per Square Meter (amount/sqm)",
    )
    available_plot_sizes = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="Available Plot Sizes (sqm)",
        help_text="Comma-separated sizes e.g. 500, 600, 1000",
    )
    min_price_other_properties = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Min Price - Other Properties",
    )
    max_price_other_properties = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Max Price - Other Properties",
    )
    estate_status = models.CharField(
        max_length=50,
        choices=ESTATE_STATUS_CHOICES,
        verbose_name="Estate Status",
    )
    total_area = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Total Area",
    )
    area_unit = models.CharField(
        max_length=20,
        choices=AREA_UNIT_CHOICES,
        default="sqm",
        verbose_name="Area Unit",
    )

    # Amenities & Infrastructure
    has_roads = models.BooleanField(default=False, verbose_name="Roads")
    has_electricity = models.BooleanField(default=False, verbose_name="Electricity")
    has_water = models.BooleanField(default=False, verbose_name="Water")
    has_fencing = models.BooleanField(default=False, verbose_name="Fencing")
    has_security = models.BooleanField(default=False, verbose_name="Security")
    has_drainage = models.BooleanField(default=False, verbose_name="Drainage")
    has_recreation = models.BooleanField(default=False, verbose_name="Recreation")

    # Tags
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Tags",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
    )

    legal_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Legal Fee",
    )

    development_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Development Fee",
    )

    receipt_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Receipt Fee",
    )

    class Meta:
        app_label = "user"
        verbose_name = "Estate"
        verbose_name_plural = "Estates"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["estate_code"]),
            models.Index(fields=["estate_type"]),
            models.Index(fields=["estate_status"]),
        ]

    def __str__(self):
        return f"{self.estate_name} ({self.estate_code})"

    def clean(self):
        super().clean()
        if not self.estate_name or not self.estate_name.strip():
            raise ValidationError({"estate_name": "Estate name cannot be blank."})
        if not self.estate_code or not self.estate_code.strip():
            raise ValidationError({"estate_code": "Estate code cannot be blank."})
        valid_types = [c[0] for c in self.ESTATE_TYPE_CHOICES]
        if self.estate_type and self.estate_type not in valid_types:
            raise ValidationError(
                {
                    "estate_type": f"Invalid type. Must be one of: {', '.join(valid_types)}"
                }
            )
        valid_statuses = [c[0] for c in self.ESTATE_STATUS_CHOICES]
        if self.estate_status and self.estate_status not in valid_statuses:
            raise ValidationError(
                {
                    "estate_status": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                }
            )
        if self.min_price_other_properties and self.max_price_other_properties:
            if self.min_price_other_properties > self.max_price_other_properties:
                raise ValidationError(
                    {"min_price_other_properties": "Min price cannot exceed max price."}
                )

    def save(self, *args, **kwargs):
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)


class EstateDocument(BaseModel):
    """Documents and files for an estate (maps, layouts, images, etc.)"""

    estate = models.ForeignKey(
        Estate,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Estate",
    )
    file = models.FileField(
        upload_to="estates/documents/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "png", "jpg", "jpeg", "doc", "docx"]
            )
        ],
        verbose_name="File",
        help_text="PDF, Image (PNG, JPG), or Document (DOC, DOCX). Max size 10MB.",
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Caption",
    )

    class Meta:
        app_label = "user"
        verbose_name = "Estate Document"
        verbose_name_plural = "Estate Documents"
        ordering = ["created_at"]

    def __str__(self):
        return f"Document for {self.estate.estate_name}"


class Property(BaseModel):
    """Model for individual properties within an estate (plots, residential, commercial)"""

    owner = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="properties",
        verbose_name="Owner",
    )

    is_our_property = models.BooleanField(
        default=True,
        verbose_name="Is Our Property",
        help_text="Indicates if this property is developed by our company.",
    )

    PROPERTY_TYPE_CHOICES = [
        ("plot", "Plot of Land"),
        ("residential", "Residential Building"),
        ("commercial", "Commercial Building"),
    ]

    PROPERTY_STATUS_CHOICES = [
        ("not-for-sale", "Not for Sale"),
        ("available", "Available"),
        ("reserved", "Reserved"),
        ("sold", "Sold"),
        ("hold", "Hold"),
    ]

    RESIDENTIAL_TYPE_CHOICES = [
        ("house", "House"),
        ("villa", "Villa"),
        ("apartment", "Apartment"),
        ("townhouse", "Townhouse"),
        ("duplex", "Duplex"),
        ("bungalow", "Bungalow"),
        ("penthouse", "Penthouse"),
    ]

    COMMERCIAL_TYPE_CHOICES = [
        ("office", "Office"),
        ("retail", "Retail Space"),
        ("warehouse", "Warehouse"),
        ("shopping_mall", "Shopping Mall"),
        ("hotel", "Hotel"),
        ("mixed_use", "Mixed Use"),
    ]

    AREA_UNIT_CHOICES = [
        ("sqft", "Square Feet"),
        ("sqm", "Square Meters"),
        ("acres", "Acres"),
        ("hectares", "Hectares"),
    ]

    # --- Common fields (all property types) ---
    estate = models.ForeignKey(
        Estate,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="properties",
        verbose_name="Estate",
    )
    property_type = models.CharField(
        max_length=20,
        choices=PROPERTY_TYPE_CHOICES,
        verbose_name="Property Type",
    )
    property_name = models.CharField(
        max_length=255,
        verbose_name="Property Name",
        help_text="e.g. Plot A-101, Villa Unit B-15, Office Block C-01",
    )
    price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Price",
    )

    boundary = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Boundary Coordinates",
        help_text='List of {lat, lng} points defining the property boundary polygon. e.g. [{"lat": 6.5244, "lng": 3.3792}, ...]',
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
    )
    status = models.CharField(
        max_length=20,
        choices=PROPERTY_STATUS_CHOICES,
        default="available",
        verbose_name="Status",
    )

    # --- Plot-specific fields ---
    plot_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Plot Number",
        help_text="Sequential plot number within the estate, e.g. 1, 2, 3...",
    )
    client_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Client / Reservation Holder",
        help_text="Free-form name of the client or reservation holder for this property.",
    )
    plot_size = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Plot Size",
    )
    plot_size_unit = models.CharField(
        max_length=20,
        choices=AREA_UNIT_CHOICES,
        default="acres",
        blank=True,
        verbose_name="Plot Size Unit",
    )

    # --- Residential-specific fields ---
    building_type_residential = models.CharField(
        max_length=50,
        choices=RESIDENTIAL_TYPE_CHOICES,
        blank=True,
        default="",
        verbose_name="Residential Building Type",
    )
    bedrooms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Bedrooms",
    )
    bathrooms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Bathrooms",
    )
    floors_residential = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Floors",
    )
    total_area_residential = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Total Area (sqft)",
    )

    # --- Commercial-specific fields ---
    building_type_commercial = models.CharField(
        max_length=50,
        choices=COMMERCIAL_TYPE_CHOICES,
        blank=True,
        default="",
        verbose_name="Commercial Building Type",
    )
    total_area_commercial = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Total Area (sqft)",
    )
    number_of_floors = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Number of Floors",
    )
    units_offices = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Units/Offices",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
    )

    class Meta:
        app_label = "user"
        verbose_name = "Property"
        verbose_name_plural = "Properties"
        ordering = ["property_name"]
        indexes = [
            models.Index(fields=["estate", "status"]),
            models.Index(fields=["property_type"]),
            models.Index(fields=["estate", "plot_number"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["estate", "property_name"],
                condition=models.Q(estate__isnull=False),
                name="unique_property_name_per_estate",
            ),
        ]

    def __str__(self):
        if self.estate:
            return f"{self.property_name} - {self.estate.estate_name}"
        return self.property_name

    @property
    def building_type(self):
        if self.property_type == "residential":
            return self.building_type_residential
        elif self.property_type == "commercial":
            return self.building_type_commercial
        return ""

    @property
    def total_area(self):
        if self.property_type == "residential":
            return self.total_area_residential
        elif self.property_type == "commercial":
            return self.total_area_commercial
        return None

    @property
    def floors(self):
        if self.property_type == "residential":
            return self.floors_residential
        elif self.property_type == "commercial":
            return self.number_of_floors
        return None

    def clean(self):
        super().clean()
        if not self.property_name or not self.property_name.strip():
            raise ValidationError({"property_name": "Property name cannot be blank."})

        if self.property_type == "plot":
            if not self.plot_size or self.plot_size <= 0:
                raise ValidationError(
                    {"plot_size": "Plot size must be greater than zero."}
                )

        elif self.property_type == "residential":
            if not self.building_type_residential:
                raise ValidationError(
                    {
                        "building_type_residential": "Building type is required for residential properties."
                    }
                )
            if not self.bedrooms:
                raise ValidationError(
                    {
                        "bedrooms": "Number of bedrooms is required for residential properties."
                    }
                )
            if not self.bathrooms:
                raise ValidationError(
                    {
                        "bathrooms": "Number of bathrooms is required for residential properties."
                    }
                )
            if not self.total_area_residential or self.total_area_residential <= 0:
                raise ValidationError(
                    {
                        "total_area_residential": "Total area is required for residential properties."
                    }
                )

        elif self.property_type == "commercial":
            if not self.building_type_commercial:
                raise ValidationError(
                    {
                        "building_type_commercial": "Building type is required for commercial properties."
                    }
                )
            if not self.total_area_commercial or self.total_area_commercial <= 0:
                raise ValidationError(
                    {
                        "total_area_commercial": "Total area is required for commercial properties."
                    }
                )
            if not self.number_of_floors:
                raise ValidationError(
                    {
                        "number_of_floors": "Number of floors is required for commercial properties."
                    }
                )

    def save(self, *args, **kwargs):
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)


class PropertyImage(BaseModel):
    """Images for a property"""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Property",
    )
    image = models.FileField(
        upload_to="estates/properties/images/",
        validators=[FileExtensionValidator(allowed_extensions=["png", "jpg", "jpeg"])],
        verbose_name="Image",
        help_text="PNG, JPG up to 10MB",
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Caption",
    )

    class Meta:
        app_label = "user"
        verbose_name = "Property Image"
        verbose_name_plural = "Property Images"
        ordering = ["created_at"]

    def __str__(self):
        return f"Image for {self.property.property_name}"
