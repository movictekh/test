from urllib.parse import urlparse

from domains.real_estate.location import normalize_boundary
from domains.real_estate.models.brokerage import BrokerageListing, BrokerageListingImage


def _file_path(url):
    return urlparse(url).path.lstrip("/") if url.startswith("http") else url


def save_listing_images(listing, urls):
    for url in urls:
        BrokerageListingImage.objects.create(listing=listing, image=_file_path(url))


def replace_listing_images(listing, urls):
    for image in listing.images.all():
        image.image.delete(save=False)
    listing.images.all().delete()
    save_listing_images(listing, urls)


def create_brokerage_listing(payload):
    data = payload.dict(exclude={"images", "tags", "boundary"})
    data = {key: value for key, value in data.items() if value is not None}
    boundary = normalize_boundary(payload.boundary)
    assigned_agent_id = data.pop("assigned_agent_id", None)
    estate_id = data.pop("estate_id", None)
    listing = BrokerageListing.objects.create(
        **data,
        boundary=boundary,
        tags=payload.tags or [],
        assigned_agent_id=assigned_agent_id,
        estate_id=estate_id,
    )
    if payload.images:
        save_listing_images(listing, payload.images)
    return listing


def update_brokerage_listing(listing, payload):
    data = payload.dict(exclude_unset=True)
    if "images" in data:
        urls = data.pop("images")
        if urls is not None:
            replace_listing_images(listing, urls)
    if "boundary" in data:
        listing.boundary = normalize_boundary(data.pop("boundary"))
    if "assigned_agent_id" in data:
        listing.assigned_agent_id = data.pop("assigned_agent_id")
    if "estate_id" in data:
        listing.estate_id = data.pop("estate_id")
    for field, value in data.items():
        if value is not None:
            setattr(listing, field, value)
    listing.full_clean()
    listing.save()
    listing.refresh_from_db()
    return listing


def verify_brokerage_listing(listing, status):
    listing.verification_status = status
    listing.save(update_fields=["verification_status", "updated_at"])
    listing.refresh_from_db()
    return listing


def delete_brokerage_listing(listing):
    listing.delete()
