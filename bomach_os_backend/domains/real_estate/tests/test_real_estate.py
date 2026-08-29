from decimal import Decimal

from django.test import TestCase

from domains.real_estate.models.brokerage import BrokerageListing
from domains.real_estate.models.estate import Estate, Property
from user.tests.helpers import RoleAPITestMixin


class RealEstateAPITests(RoleAPITestMixin, TestCase):
    def setUp(self):
        self.role = self.create_role(
            "Real Estate Manager",
            {
                "estates": ["create", "view", "list", "update", "delete"],
                "properties": ["create", "view", "list", "update", "delete"],
                "brokerage": ["create", "view", "list", "update", "delete"],
            },
        )
        self.employee = self.create_user_with_employee(
            email="estate@example.com",
            username="estateadmin",
            employee_id="EMP-ESTATE-01",
            role=self.role,
        )
        self.headers = self.auth_headers(self.employee)

        self.estate = Estate.objects.create(
            estate_name="Fortress City",
            estate_code="EST-TEST-001",
            estate_type="residential",
            developer_company_name="Bomach Group",
            estate_description="Test estate",
            country="Nigeria",
            state="Enugu",
            city_town="Enugu",
            precise_address="Owoh, Enugu",
            price_per_sqm=Decimal("40000.00"),
            estate_status="available",
        )
        for i in range(1, 5):
            Property.objects.create(
                estate=self.estate,
                property_type="plot",
                property_name=f"Plot {i:02d}",
                plot_number=i,
                price=Decimal("4500000.00"),
                plot_size=Decimal("450.00"),
                status="sold" if i <= 2 else ("reserved" if i == 3 else "available"),
                client_name="Test Client" if i <= 3 else "",
            )

    # ============== Estate Stats ==============

    def test_estate_stats(self):
        response = self.client.get(
            f"/api/v1/estates/{self.estate.id}/stats",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 4)
        self.assertEqual(data["sold"], 2)
        self.assertEqual(data["reserved"], 1)
        self.assertEqual(data["available"], 1)
        self.assertEqual(data["hold"], 0)
        self.assertEqual(Decimal(data["total_value"]), Decimal("18000000"))

    def test_estate_stats_404(self):
        response = self.client.get("/api/v1/estates/99999/stats", **self.headers)
        self.assertEqual(response.status_code, 404)

    # ============== Estate Layout ==============

    def test_estate_layout(self):
        response = self.client.get(
            f"/api/v1/estates/{self.estate.id}/layout",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 4)
        first = data[0]
        self.assertEqual(first["plot_number"], 1)
        self.assertEqual(first["status"], "sold")
        self.assertIn("status_display", first)
        self.assertIn("price", first)
        self.assertIn("client_name", first)

    # ============== Plot Quick-Update ==============

    def test_quick_update_plot(self):
        plot = Property.objects.get(estate=self.estate, plot_number=4)
        response = self.client.patch(
            f"/api/v1/estates/{self.estate.id}/plots/{plot.id}/quick-update",
            data={
                "status": "hold",
                "client_name": "Reserved Client",
                "price": "5000000",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "hold")
        self.assertEqual(data["client_name"], "Reserved Client")
        self.assertEqual(data["price"], "5000000.00")
        plot.refresh_from_db()
        self.assertEqual(plot.status, "hold")
        self.assertEqual(plot.client_name, "Reserved Client")

    def test_quick_update_invalid_status(self):
        plot = Property.objects.get(estate=self.estate, plot_number=4)
        response = self.client.patch(
            f"/api/v1/estates/{self.estate.id}/plots/{plot.id}/quick-update",
            data={"status": "bogus"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)

    # ============== Brokerage Listings ==============

    def test_create_brokerage_listing(self):
        response = self.client.post(
            "/api/v1/brokerage/",
            data={
                "title": "4-bedroom duplex",
                "location": "Independence Layout, Enugu",
                "price": "185000000.00",
                "property_type": "residential",
                "owner_name": "Mr Nnamdi",
                "owner_phone": "08012345678",
                "commission_rate": "5.00",
                "verification_status": "pending",
                "status": "available",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["title"], "4-bedroom duplex")
        self.assertEqual(data["verification_status_display"], "Pending Verification")
        self.assertEqual(data["property_type_display"], "Residential")

    def test_list_brokerage_listings(self):
        BrokerageListing.objects.create(
            title="Commercial warehouse",
            location="Emene, Enugu",
            price=Decimal("95000000.00"),
            property_type="commercial",
            owner_name="Apex Holdings",
            verification_status="inspection_due",
            status="available",
        )
        response = self.client.get("/api/v1/brokerage/", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["title"], "Commercial warehouse")

    def test_get_brokerage_listing(self):
        listing = BrokerageListing.objects.create(
            title="5-bedroom villa",
            location="GRA, Enugu",
            price=Decimal("120000000.00"),
            property_type="residential",
            owner_name="Mrs Obi",
            verification_status="verified",
            status="available",
        )
        response = self.client.get(f"/api/v1/brokerage/{listing.id}", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "5-bedroom villa")
        self.assertEqual(data["verification_status_display"], "Verified")

    def test_update_brokerage_listing(self):
        listing = BrokerageListing.objects.create(
            title="Old title",
            location="Enugu",
            price=Decimal("10000000.00"),
            property_type="land",
            owner_name="Owner",
            verification_status="pending",
            status="available",
        )
        response = self.client.put(
            f"/api/v1/brokerage/{listing.id}",
            data={"title": "New title", "price": "12000000.00"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        listing.refresh_from_db()
        self.assertEqual(listing.title, "New title")
        self.assertEqual(listing.price, Decimal("12000000.00"))

    def test_verify_brokerage_listing(self):
        listing = BrokerageListing.objects.create(
            title="Warehouse",
            location="Emene",
            price=Decimal("50000000.00"),
            property_type="commercial",
            owner_name="Owner",
            verification_status="pending",
            status="available",
        )
        response = self.client.patch(
            f"/api/v1/brokerage/{listing.id}/verify",
            data={"verification_status": "verified"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["verification_status"], "verified")
        self.assertEqual(data["verification_status_display"], "Verified")

    def test_verify_brokerage_listing_invalid(self):
        listing = BrokerageListing.objects.create(
            title="Warehouse",
            location="Emene",
            price=Decimal("50000000.00"),
            property_type="commercial",
            owner_name="Owner",
            verification_status="pending",
            status="available",
        )
        response = self.client.patch(
            f"/api/v1/brokerage/{listing.id}/verify",
            data={"verification_status": "bogus"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_brokerage_listing(self):
        listing = BrokerageListing.objects.create(
            title="Duplex",
            location="Enugu",
            price=Decimal("50000000.00"),
            property_type="residential",
            owner_name="Owner",
            verification_status="pending",
            status="available",
        )
        response = self.client.delete(f"/api/v1/brokerage/{listing.id}", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(BrokerageListing.objects.filter(id=listing.id).exists())

    def test_brokerage_stats(self):
        BrokerageListing.objects.create(
            title="Verified duplex",
            location="Enugu",
            price=Decimal("100000000.00"),
            property_type="residential",
            owner_name="A",
            verification_status="verified",
            status="available",
        )
        BrokerageListing.objects.create(
            title="Sold warehouse",
            location="Enugu",
            price=Decimal("50000000.00"),
            property_type="commercial",
            owner_name="B",
            verification_status="verified",
            status="sold",
        )
        response = self.client.get("/api/v1/brokerage/stats", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["verified"], 2)
        self.assertEqual(data["sold"], 1)
        self.assertEqual(data["available"], 1)
        self.assertEqual(Decimal(data["total_listing_value"]), Decimal("150000000"))

    def test_brokerage_choices(self):
        response = self.client.get("/api/v1/brokerage/choices/fields", **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("verification_status", data)
        self.assertIn("listing_status", data)
        self.assertIn("property_type", data)


class RealEstatePermissionsTests(RoleAPITestMixin, TestCase):
    def test_brokerage_requires_permission(self):
        role = self.create_role(
            "Restricted",
            {
                "estates": ["list"],
                "properties": ["list"],
            },
        )
        employee = self.create_user_with_employee(
            email="restricted@example.com",
            username="restricted",
            employee_id="EMP-RESTRICTED",
            role=role,
        )
        response = self.client.get("/api/v1/brokerage/", **self.auth_headers(employee))
        self.assertEqual(response.status_code, 403)
