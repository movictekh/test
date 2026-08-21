from pydantic import ValidationError

from django.test import TestCase

from hr.api.schemas.asset import AssetCreate, AssetUpdate
from hr.models.asset import Asset


class AssetSchemaTests(TestCase):
    def test_create_asset_allows_optional_identifiers_and_documents(self):
        payload = AssetCreate(
            name="MacBook Pro 16",
            asset_type="Laptop",
            branch="Enugu Branch",
            manufacturer="Apple",
        )

        data = payload.model_dump()

        self.assertEqual(data["asset_type"], "laptop")
        self.assertIsNone(data["serial_number"])
        self.assertIsNone(data["imei"])
        self.assertEqual(data["documents"], [])

    def test_create_asset_accepts_document_and_image_documents(self):
        payload = AssetCreate(
            name="MacBook Pro 16",
            asset_type="Laptop",
            branch="Enugu Branch",
            documents=[
                {"name": "receipt.pdf", "type": "Document"},
                {
                    "name": "asset-photo.jpg",
                    "url": "https://example.com/asset-photo.jpg",
                    "type": "Image",
                },
            ],
        )

        asset = Asset.objects.create(**payload.model_dump())

        self.assertEqual(asset.asset_type, "laptop")
        self.assertEqual(
            asset.documents,
            [
                {"name": "receipt.pdf", "type": "Document", "url": None},
                {
                    "name": "asset-photo.jpg",
                    "type": "Image",
                    "url": "https://example.com/asset-photo.jpg",
                },
            ],
        )

    def test_create_asset_rejects_json_encoded_documents_string(self):
        with self.assertRaises(ValidationError):
            AssetCreate(
                name="MacBook Pro 16",
                asset_type="Laptop",
                branch="Enugu Branch",
                documents='[{"name":"receipt.pdf","type":"Document"}]',
            )

    def test_create_asset_rejects_unknown_document_type(self):
        with self.assertRaises(ValidationError):
            AssetCreate(
                name="MacBook Pro 16",
                asset_type="Laptop",
                branch="Enugu Branch",
                documents=[{"name": "receipt.pdf", "type": "Receipt"}],
            )

    def test_create_asset_rejects_unknown_asset_type(self):
        with self.assertRaises(ValidationError):
            AssetCreate(
                name="MacBook Pro 16",
                asset_type="Computer",
                branch="Enugu Branch",
            )

    def test_update_asset_can_replace_imei_and_documents(self):
        payload = AssetUpdate(
            imei="351756051523456",
            documents=[{"name": "receipt.pdf", "type": "Document"}],
        )

        self.assertEqual(
            payload.model_dump(exclude_unset=True),
            {
                "imei": "351756051523456",
                "documents": [{"name": "receipt.pdf", "type": "Document"}],
            },
        )

    def test_update_asset_rejects_null_documents(self):
        with self.assertRaises(ValidationError):
            AssetUpdate(documents=None)
