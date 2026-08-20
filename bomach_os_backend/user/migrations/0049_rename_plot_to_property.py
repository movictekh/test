import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


def migrate_plot_data_forward(apps, schema_editor):
    """Set property_type='plot' and price from estate price_per_sqm * plot_size for existing plots"""
    Property = apps.get_model("user", "Property")
    for prop in Property.objects.select_related("estate").all():
        prop.property_type = "plot"
        prop.price = prop.estate.price_per_sqm * prop.plot_size
        prop.save(update_fields=["property_type", "price"])


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0048_create_plot_models"),
    ]

    operations = [
        # Step 1: Rename Plot -> Property
        migrations.RenameModel(
            old_name="Plot",
            new_name="Property",
        ),
        # Step 2: Rename PlotImage -> PropertyImage
        migrations.RenameModel(
            old_name="PlotImage",
            new_name="PropertyImage",
        ),
        # Step 3: Rename the FK in PropertyImage from 'plot' to 'property'
        migrations.RenameField(
            model_name="propertyimage",
            old_name="plot",
            new_name="property",
        ),
        # Step 4: Rename plot_name -> property_name
        migrations.RenameField(
            model_name="property",
            old_name="plot_name",
            new_name="property_name",
        ),
        # Step 5: Update property_name max_length and help_text
        migrations.AlterField(
            model_name="property",
            name="property_name",
            field=models.CharField(
                help_text="e.g. Plot A-101, Villa Unit B-15, Office Block C-01",
                max_length=255,
                verbose_name="Property Name",
            ),
        ),
        # Step 6: Make plot_size nullable (it's only required for plot type now)
        migrations.AlterField(
            model_name="property",
            name="plot_size",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="Plot Size",
            ),
        ),
        # Step 7: Add property_type field
        migrations.AddField(
            model_name="property",
            name="property_type",
            field=models.CharField(
                choices=[
                    ("plot", "Plot of Land"),
                    ("residential", "Residential Building"),
                    ("commercial", "Commercial Building"),
                ],
                default="plot",
                max_length=20,
                verbose_name="Property Type",
            ),
            preserve_default=False,
        ),
        # Step 8: Add price field (will be populated from data migration)
        migrations.AddField(
            model_name="property",
            name="price",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.01"),
                max_digits=15,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="Price",
            ),
            preserve_default=False,
        ),
        # Step 9: Add plot_size_unit
        migrations.AddField(
            model_name="property",
            name="plot_size_unit",
            field=models.CharField(
                blank=True,
                choices=[
                    ("sqft", "Square Feet"),
                    ("sqm", "Square Meters"),
                    ("acres", "Acres"),
                    ("hectares", "Hectares"),
                ],
                default="acres",
                max_length=20,
                verbose_name="Plot Size Unit",
            ),
        ),
        # Step 10: Add residential fields
        migrations.AddField(
            model_name="property",
            name="building_type_residential",
            field=models.CharField(
                blank=True,
                choices=[
                    ("house", "House"),
                    ("villa", "Villa"),
                    ("apartment", "Apartment"),
                    ("townhouse", "Townhouse"),
                    ("duplex", "Duplex"),
                    ("bungalow", "Bungalow"),
                    ("penthouse", "Penthouse"),
                ],
                default="",
                max_length=50,
                verbose_name="Residential Building Type",
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="bedrooms",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="Bedrooms"
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="bathrooms",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="Bathrooms"
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="floors_residential",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="Floors"
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="total_area_residential",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="Total Area (sqft)",
            ),
        ),
        # Step 11: Add commercial fields
        migrations.AddField(
            model_name="property",
            name="building_type_commercial",
            field=models.CharField(
                blank=True,
                choices=[
                    ("office", "Office"),
                    ("retail", "Retail Space"),
                    ("warehouse", "Warehouse"),
                    ("shopping_mall", "Shopping Mall"),
                    ("hotel", "Hotel"),
                    ("mixed_use", "Mixed Use"),
                ],
                default="",
                max_length=50,
                verbose_name="Commercial Building Type",
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="total_area_commercial",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="Total Area (sqft)",
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="number_of_floors",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="Number of Floors"
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="units_offices",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="Units/Offices"
            ),
        ),
        # Step 12: Update meta BEFORE data migration (fixes ordering reference to old field)
        migrations.AlterModelOptions(
            name="property",
            options={
                "ordering": ["property_name"],
                "verbose_name": "Property",
                "verbose_name_plural": "Properties",
            },
        ),
        migrations.AlterModelOptions(
            name="propertyimage",
            options={
                "ordering": ["created_at"],
                "verbose_name": "Property Image",
                "verbose_name_plural": "Property Images",
            },
        ),
        # Step 13: Data migration - set property_type and price for existing plots
        migrations.RunPython(
            migrate_plot_data_forward,
            migrations.RunPython.noop,
        ),
        # Step 14: Update related_name on estate FK
        migrations.AlterField(
            model_name="property",
            name="estate",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="properties",
                to="user.estate",
                verbose_name="Estate",
            ),
        ),
        # Step 15: Update PropertyImage FK and upload path
        migrations.AlterField(
            model_name="propertyimage",
            name="property",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="images",
                to="user.property",
                verbose_name="Property",
            ),
        ),
        migrations.AlterField(
            model_name="propertyimage",
            name="image",
            field=models.FileField(
                help_text="PNG, JPG up to 10MB",
                upload_to="estates/properties/images/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["png", "jpg", "jpeg"]
                    )
                ],
                verbose_name="Image",
            ),
        ),
        # Step 16: Remove old unique_together and add new one
        migrations.AlterUniqueTogether(
            name="property",
            unique_together={("estate", "property_name")},
        ),
        # Step 17: Remove old indexes and add new ones
        migrations.AddIndex(
            model_name="property",
            index=models.Index(
                fields=["property_type"], name="user_proper_propert_190372_idx"
            ),
        ),
    ]
