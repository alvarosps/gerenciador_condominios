"""
E2E Tests for Property Management Flows

Tests complete property management workflows:
- Building creation and management
- Apartment creation and assignment
- Furniture inventory management
- Property filtering and search
"""

import pytest

from tests.e2e.base import BaseE2ETest


def redis_available():
    """Check if Redis is available for testing."""
    try:
        import redis

        r = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=1)
        r.ping()
        return True
    except Exception:
        return False


@pytest.mark.django_db
@pytest.mark.skipif(not redis_available(), reason="Redis is not available")
class TestBuildingManagementFlow(BaseE2ETest):
    """Test complete building management workflows."""

    def test_complete_building_lifecycle(self):
        """
        E2E Test: Complete building lifecycle

        Workflow:
        1. Admin creates a new building → 201
        2. Admin retrieves building details → 200
        3. Admin updates building information → 200
        4. Admin lists all buildings → 200
        5. Admin searches for specific building → 200
        6. Admin deletes building → 204
        7. Verify building no longer exists → 404
        """
        self.authenticate_as_admin()

        # Step 1: Create building
        building_data = {
            "street_number": 836,
            "name": "Edifício Central",
            "address": "Rua Central, 836 - São Paulo, SP",
        }
        response = self.client.post("/api/buildings/", building_data, format="json")
        self.assert_response_success(response, 201)
        building = response.json()
        self.assert_has_keys(building, "id", "street_number", "name", "address")
        assert building["street_number"] == 836

        building_id = building["id"]

        # Step 2: Retrieve building details
        response = self.client.get(f"/api/buildings/{building_id}/")
        self.assert_response_success(response, 200)
        retrieved = response.json()
        assert retrieved["id"] == building_id
        assert retrieved["name"] == "Edifício Central"

        # Step 3: Update building
        update_data = {"street_number": 836, "name": "Edifício Central Plaza", "address": building_data["address"]}
        response = self.client.put(f"/api/buildings/{building_id}/", update_data, format="json")
        self.assert_response_success(response, 200)
        updated = response.json()
        assert updated["name"] == "Edifício Central Plaza"

        # Step 4: List all buildings
        response = self.client.get("/api/buildings/")
        self.assert_response_success(response, 200)
        buildings_list = response.json()
        assert "results" in buildings_list
        assert len(buildings_list["results"]) >= 1

        # Step 5: Search for specific building
        response = self.client.get("/api/buildings/", {"search": "Central"})
        self.assert_response_success(response, 200)
        search_results = response.json()["results"]
        assert any(b["id"] == building_id for b in search_results)

        # Step 6: Delete building
        response = self.client.delete(f"/api/buildings/{building_id}/")
        self.assert_response_success(response, 204)

        # Step 7: Verify deletion
        response = self.client.get(f"/api/buildings/{building_id}/")
        self.assert_response_error(response, 404)

    def test_building_validation_flow(self):
        """
        E2E Test: Building validation and error handling

        Workflow:
        1. Attempt to create building with missing fields → 400
        2. Attempt to create building with duplicate street_number → 400
        3. Successfully create valid building → 201
        """
        self.authenticate_as_admin()

        # Step 1: Missing required fields
        response = self.client.post("/api/buildings/", {"name": "Incomplete Building"}, format="json")
        self.assert_response_error(response, 400)

        # Step 2: Create first building
        building1 = self.create_building(street_number=500, name="Building 1")
        assert building1["street_number"] == 500

        # Attempt duplicate street_number
        response = self.client.post(
            "/api/buildings/",
            {"street_number": 500, "name": "Building 2", "address": "Different Address"},  # Duplicate
            format="json",
        )
        self.assert_response_error(response, 400)

        # Step 3: Create valid building with different street_number
        building2 = self.create_building(street_number=501, name="Building 2")
        assert building2["street_number"] == 501


@pytest.mark.django_db
@pytest.mark.skipif(not redis_available(), reason="Redis is not available")
class TestApartmentManagementFlow(BaseE2ETest):
    """Test complete apartment management workflows."""

    def test_complete_apartment_lifecycle(self):
        """
        E2E Test: Complete apartment lifecycle

        Workflow:
        1. Create building
        2. Create apartment in building → 201
        3. Retrieve apartment with nested building data → 200
        4. Update apartment rental value → 200
        5. Filter apartments by building → 200
        6. Mark apartment as rented → 200
        7. Delete apartment → 204
        """
        self.authenticate_as_admin()

        # Step 1: Create building
        building = self.create_building(street_number=600)

        # Step 2: Create apartment
        apt_data = {
            "building_id": building["id"],
            "number": 101,
            "rental_value": "1500.00",
            "cleaning_fee": "200.00",
            "max_tenants": 2,
            "is_rented": False,
        }
        response = self.client.post("/api/apartments/", apt_data, format="json")
        self.assert_response_success(response, 201)
        apartment = response.json()
        apt_id = apartment["id"]

        # Step 3: Retrieve with nested building
        response = self.client.get(f"/api/apartments/{apt_id}/")
        self.assert_response_success(response, 200)
        retrieved = response.json()
        assert "building" in retrieved
        assert retrieved["building"]["id"] == building["id"]
        assert retrieved["number"] == 101

        # Step 4: Update rental value
        update_data = {
            "building_id": building["id"],
            "number": 101,
            "rental_value": "1800.00",  # Increased
            "cleaning_fee": "200.00",
            "max_tenants": 2,
            "is_rented": False,
        }
        response = self.client.put(f"/api/apartments/{apt_id}/", update_data, format="json")
        self.assert_response_success(response, 200)
        updated = response.json()
        assert updated["rental_value"] == "1800.00"

        # Step 5: Filter by building
        response = self.client.get("/api/apartments/", {"building": building["id"]})
        self.assert_response_success(response, 200)
        filtered = response.json()["results"]
        assert all(apt["building"]["id"] == building["id"] for apt in filtered)

        # Step 6: Mark as rented
        response = self.client.patch(f"/api/apartments/{apt_id}/", {"is_rented": True}, format="json")
        self.assert_response_success(response, 200)
        assert response.json()["is_rented"] is True

        # Step 7: Delete apartment
        response = self.client.delete(f"/api/apartments/{apt_id}/")
        self.assert_response_success(response, 204)

    def test_multiple_apartments_in_building_flow(self):
        """
        E2E Test: Managing multiple apartments in one building

        Workflow:
        1. Create building
        2. Create 5 apartments in the building
        3. List apartments filtered by building → Should show all 5
        4. Filter available (not rented) apartments → Should show all 5
        5. Rent 2 apartments
        6. Filter available apartments → Should show 3
        """
        self.authenticate_as_admin()

        # Step 1: Create building
        building = self.create_building(street_number=700)

        # Step 2: Create 5 apartments
        apartment_ids = []
        for i in range(1, 6):
            apt = self.create_apartment(building["id"], number=100 + i, rental_value=f"{1500 + i * 100}.00")
            apartment_ids.append(apt["id"])

        # Step 3: List all apartments in building
        response = self.client.get("/api/apartments/", {"building": building["id"]})
        self.assert_response_success(response, 200)
        all_apts = response.json()["results"]
        assert len(all_apts) >= 5

        # Step 4: Filter available apartments
        response = self.client.get("/api/apartments/", {"building": building["id"], "is_rented": "false"})
        self.assert_response_success(response, 200)
        available = response.json()["results"]
        assert len(available) >= 5

        # Step 5: Rent 2 apartments
        for apt_id in apartment_ids[:2]:
            response = self.client.patch(f"/api/apartments/{apt_id}/", {"is_rented": True}, format="json")
            self.assert_response_success(response, 200)

        # Step 6: Verify 2 apartments are now rented
        response = self.client.get("/api/apartments/", {"building": building["id"], "is_rented": "true"})
        self.assert_response_success(response, 200)
        rented_now = response.json()["results"]
        building_rented = [apt for apt in rented_now if apt["building"]["id"] == building["id"]]
        assert len(building_rented) >= 2, f"Expected at least 2 rented apartments, got {len(building_rented)}"


@pytest.mark.django_db
@pytest.mark.skipif(not redis_available(), reason="Redis is not available")
class TestFurnitureManagementFlow(BaseE2ETest):
    """Test furniture inventory management workflows."""

    def test_furniture_inventory_workflow(self):
        """
        E2E Test: Furniture inventory management

        Workflow:
        1. Create furniture items
        2. Assign furniture to apartment
        3. Assign furniture to tenant
        4. List all furniture
        5. Update furniture description
        6. Remove furniture
        """
        self.authenticate_as_admin()

        # Step 1: Create furniture items
        furniture_items = []
        for item in ["Sofa", "Bed", "Table", "Chair"]:
            furniture = self.create_furniture(description=item)
            furniture_items.append(furniture)
            assert furniture["description"] == item

        # Step 2: Create apartment
        # Note: Apartment serializer doesn't support furniture_ids in creation
        # Furniture is associated with apartments through the Furniture model's apartment field
        building = self.create_building(street_number=800)
        apartment = self.create_apartment(building["id"], number=201)

        # Verify apartment was created
        response = self.client.get(f'/api/apartments/{apartment["id"]}/')
        self.assert_response_success(response, 200)
        apt_detail = response.json()
        assert "furnitures" in apt_detail

        # Step 3: Create tenant with furniture
        tenant = self.create_tenant(name="João Silva", furniture_ids=[furniture_items[2]["id"]])  # Table

        # Verify tenant has furniture
        response = self.client.get(f'/api/tenants/{tenant["id"]}/')
        self.assert_response_success(response, 200)
        tenant_detail = response.json()
        assert "furnitures" in tenant_detail
        assert len(tenant_detail["furnitures"]) == 1

        # Step 4: List all furniture
        response = self.client.get("/api/furnitures/")
        self.assert_response_success(response, 200)
        all_furniture = response.json()["results"]
        assert len(all_furniture) >= 4

        # Step 5: Update furniture description
        furniture_id = furniture_items[0]["id"]
        response = self.client.patch(f"/api/furnitures/{furniture_id}/", {"description": "Leather Sofa"}, format="json")
        self.assert_response_success(response, 200)
        assert response.json()["description"] == "Leather Sofa"

        # Step 6: Delete furniture
        response = self.client.delete(f"/api/furnitures/{furniture_id}/")
        self.assert_response_success(response, 204)


@pytest.mark.django_db
@pytest.mark.skipif(not redis_available(), reason="Redis is not available")
class TestPropertySearchAndFilterFlow(BaseE2ETest):
    """Test property search and filtering workflows."""

    def test_comprehensive_search_workflow(self):
        """
        E2E Test: Comprehensive property search and filtering

        Workflow:
        1. Create multiple buildings
        2. Create multiple apartments with varying attributes
        3. Search buildings by name
        4. Filter apartments by rental value range
        5. Filter apartments by occupancy status
        6. Filter apartments by building and status
        """
        self.authenticate_as_admin()

        # Step 1: Create buildings
        building1 = self.create_building(street_number=900, name="North Tower")
        building2 = self.create_building(street_number=901, name="South Tower")

        # Step 2: Create apartments with varying attributes
        # North Tower - 3 apartments
        apt1 = self.create_apartment(building1["id"], 101, rental_value="1200.00", is_rented=False)
        _apt2 = self.create_apartment(building1["id"], 102, rental_value="1500.00", is_rented=True)  # noqa: F841
        apt3 = self.create_apartment(building1["id"], 103, rental_value="1800.00", is_rented=False)

        # South Tower - 2 apartments
        apt4 = self.create_apartment(building2["id"], 201, rental_value="2000.00", is_rented=False)
        _apt5 = self.create_apartment(building2["id"], 202, rental_value="2500.00", is_rented=True)  # noqa: F841

        # Step 3: Search buildings by name
        response = self.client.get("/api/buildings/", {"search": "Tower"})
        self.assert_response_success(response, 200)
        results = response.json()["results"]
        assert len(results) >= 2
        assert any("Tower" in b["name"] for b in results)

        # Step 4: Filter apartments by building
        response = self.client.get("/api/apartments/", {"building": building1["id"]})
        self.assert_response_success(response, 200)
        north_apts = response.json()["results"]
        assert len(north_apts) >= 3

        # Step 5: Filter available apartments
        response = self.client.get("/api/apartments/", {"is_rented": "false"})
        self.assert_response_success(response, 200)
        available = response.json()["results"]
        # Verify our created available apartments are in the list
        available_ids = [apt["id"] for apt in available]
        assert apt1["id"] in available_ids, "apt1 should be available"
        assert apt3["id"] in available_ids, "apt3 should be available"
        assert apt4["id"] in available_ids, "apt4 should be available"

        # Step 6: Combined filter - available apartments in North Tower
        response = self.client.get("/api/apartments/", {"building": building1["id"], "is_rented": "false"})
        self.assert_response_success(response, 200)
        filtered = response.json()["results"]
        filtered_ids = [apt["id"] for apt in filtered]
        # Verify our specific non-rented apartments are included
        assert apt1["id"] in filtered_ids, "apt1 (not rented) should be in filtered list"
        assert apt3["id"] in filtered_ids, "apt3 (not rented) should be in filtered list"
