from decimal import Decimal
from urllib.parse import urlparse

from domains.real_estate.location import normalize_boundary
from domains.real_estate.models.estate import (
    Estate,
    EstateDocument,
    Property,
    PropertyImage,
)


def _file_path(url):
    return urlparse(url).path.lstrip("/") if url.startswith("http") else url


def save_estate_documents(estate, urls):
    for url in urls:
        EstateDocument.objects.create(estate=estate, file=_file_path(url))


def replace_estate_documents(estate, urls):
    for document in estate.documents.all():
        document.file.delete(save=False)
    estate.documents.all().delete()
    save_estate_documents(estate, urls)


def save_property_images(prop, urls):
    for url in urls:
        PropertyImage.objects.create(property=prop, image=_file_path(url))


def replace_property_images(prop, urls):
    for image in prop.images.all():
        image.image.delete(save=False)
    prop.images.all().delete()
    save_property_images(prop, urls)


def create_estate(payload):
    data = payload.dict(exclude={"documents", "tags", "boundary"})
    data = {key: value for key, value in data.items() if value is not None}
    estate = Estate.objects.create(
        **data,
        tags=payload.tags or [],
        boundary=normalize_boundary(payload.boundary),
    )
    if payload.documents:
        save_estate_documents(estate, payload.documents)
    return estate


def update_estate(estate, payload):
    data = payload.dict(exclude_unset=True)
    if "boundary" in data:
        estate.boundary = normalize_boundary(data.pop("boundary"))
    if "documents" in data:
        urls = data.pop("documents")
        if urls is not None:
            replace_estate_documents(estate, urls)
    for field, value in data.items():
        if value is not None:
            setattr(estate, field, value)
    estate.full_clean()
    estate.save()
    estate.refresh_from_db()
    return estate


def delete_estate(estate):
    estate.delete()


def create_property(payload, *, estate=None):
    data = payload.dict(exclude={"images", "boundary"})
    data = {key: value for key, value in data.items() if value is not None}
    property_boundary = normalize_boundary(payload.boundary)
    if not property_boundary and estate is not None:
        property_boundary = normalize_boundary(estate.boundary)
    if "price" not in data and estate is not None:
        if payload.property_type == "plot" and payload.plot_size:
            data["price"] = Decimal(estate.price_per_sqm) * Decimal(payload.plot_size)
        else:
            data["price"] = estate.price_per_sqm
    prop = Property.objects.create(
        estate=estate,
        boundary=property_boundary,
        **data,
    )
    if payload.images:
        save_property_images(prop, payload.images)
    return prop


def update_property(prop, payload):
    data = payload.dict(exclude_unset=True)
    if "boundary" in data:
        boundary = normalize_boundary(data.pop("boundary"))
        if not boundary and prop.estate is not None:
            boundary = normalize_boundary(prop.estate.boundary)
        prop.boundary = boundary
    if "images" in data:
        urls = data.pop("images")
        if urls is not None:
            replace_property_images(prop, urls)
    for field, value in data.items():
        if value is not None:
            setattr(prop, field, value)
    prop.full_clean()
    prop.save()
    prop.refresh_from_db()
    return prop


def delete_property(prop):
    prop.delete()


def quick_update_plot(prop, data):
    for field, value in data.items():
        if value is not None:
            setattr(prop, field, value)
    prop.full_clean()
    prop.save()
    prop.refresh_from_db()
    return prop
