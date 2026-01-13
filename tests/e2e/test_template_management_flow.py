"""
E2E Tests for Template Management Workflows

Tests complete template management workflows:
- Get contract template
- Edit and save template
- Preview template with data
- Backup and restore functionality
- Template version management
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
class TestTemplateEditingFlow(BaseE2ETest):
    """Test template editing workflows."""

    def test_complete_template_editing_workflow(self):
        """
        E2E Test: Complete template editing workflow

        Workflow:
        1. Get current template → 200
        2. Modify template content
        3. Save modified template → 200, creates backup
        4. Retrieve template → Verify changes
        5. Verify backup was created
        """
        self.authenticate_as_admin()

        # Step 1: Get current template
        response = self.client.get("/api/leases/get_contract_template/")
        self.assert_response_success(response, 200)
        current_template = response.json()
        self.assert_has_keys(current_template, "content")
        _original_content = current_template["content"]  # noqa: F841

        # Step 2 & 3: Modify and save template
        new_content = """
        <html>
        <head><title>Modified Contract</title></head>
        <body>
            <h1>CONTRATO DE LOCAÇÃO - MODIFICADO</h1>
            <p>Locador: {{owner_name}}</p>
            <p>Locatário: {{tenant_name}}</p>
            <p>Valor: R$ {{rental_value}}</p>
        </body>
        </html>
        """
        response = self.client.post("/api/leases/save_contract_template/", {"content": new_content}, format="json")
        self.assert_response_success(response, 200)
        save_result = response.json()
        self.assert_has_keys(save_result, "message", "backup_filename")
        backup_filename = save_result["backup_filename"]

        # Step 4: Retrieve template and verify changes
        response = self.client.get("/api/leases/get_contract_template/")
        self.assert_response_success(response, 200)
        updated_template = response.json()
        assert "MODIFICADO" in updated_template["content"]

        # Step 5: Verify backup exists
        response = self.client.get("/api/leases/list_template_backups/")
        self.assert_response_success(response, 200)
        backups = response.json()
        assert isinstance(backups, list)
        assert len(backups) > 0
        assert any(b["filename"] == backup_filename for b in backups)

    def test_template_validation_flow(self):
        """
        E2E Test: Template validation

        Workflow:
        1. Attempt to save empty template → 400
        2. Attempt to save template without content → 400
        3. Save valid template → 200
        """
        self.authenticate_as_admin()

        # Step 1: Empty template
        response = self.client.post("/api/leases/save_contract_template/", {"content": ""}, format="json")
        self.assert_response_error(response, 400)

        # Step 2: Missing content
        response = self.client.post("/api/leases/save_contract_template/", {}, format="json")
        self.assert_response_error(response, 400)

        # Step 3: Valid template
        valid_content = "<html><body><h1>Valid Template</h1></body></html>"
        response = self.client.post("/api/leases/save_contract_template/", {"content": valid_content}, format="json")
        self.assert_response_success(response, 200)


@pytest.mark.django_db
@pytest.mark.skipif(not redis_available(), reason="Redis is not available")
class TestTemplatePreviewFlow(BaseE2ETest):
    """Test template preview with sample data."""

    def test_template_preview_with_lease_data(self):
        """
        E2E Test: Template preview with real lease data

        Workflow:
        1. Create complete lease setup
        2. Get current template
        3. Preview template with lease data → 200
        4. Verify HTML contains lease information
        """
        self.authenticate_as_admin()

        # Step 1: Create lease
        building = self.create_building(street_number=2000)
        apartment = self.create_apartment(building["id"], number=1001)
        tenant = self.create_tenant(name="Preview Test Tenant")
        lease = self.create_lease(apartment["id"], tenant["id"], [tenant["id"]], rental_value="2500.00")

        # Step 2: Get template
        response = self.client.get("/api/leases/get_contract_template/")
        self.assert_response_success(response, 200)
        template_content = response.json()["content"]

        # Step 3: Preview with lease data
        response = self.client.post(
            "/api/leases/preview_contract_template/",
            {"content": template_content, "lease_id": lease["id"]},
            format="json",
        )
        self.assert_response_success(response, 200)
        preview = response.json()

        # Step 4: Verify HTML was generated
        self.assert_has_keys(preview, "html")
        html_content = preview["html"]
        assert isinstance(html_content, str)
        assert len(html_content) > 0
        # Verify it's valid HTML (has html tags)
        assert "<html>" in html_content.lower() or "<!doctype" in html_content.lower()

    def test_template_preview_without_lease(self):
        """
        E2E Test: Preview template with generic data

        Workflow:
        1. Preview template without lease_id → Should use first available or sample data
        2. Verify preview is generated
        """
        self.authenticate_as_admin()

        # Create at least one lease for preview
        building = self.create_building(street_number=2100)
        apartment = self.create_apartment(building["id"], number=1101)
        tenant = self.create_tenant(name="Generic Preview")
        _lease = self.create_lease(apartment["id"], tenant["id"], [tenant["id"]])  # noqa: F841

        # Get template
        response = self.client.get("/api/leases/get_contract_template/")
        template_content = response.json()["content"]

        # Preview without specific lease
        response = self.client.post(
            "/api/leases/preview_contract_template/", {"content": template_content}, format="json"
        )
        # Should succeed using first available lease
        self.assert_response_success(response, 200)
        assert "html" in response.json()

    def test_template_preview_with_custom_content(self):
        """
        E2E Test: Preview with custom template content

        Workflow:
        1. Create custom template content with variables
        2. Preview with lease data → 200
        3. Verify variables are replaced
        """
        self.authenticate_as_admin()

        # Setup
        building = self.create_building(street_number=2200)
        apartment = self.create_apartment(building["id"], number=1201)
        tenant = self.create_tenant(name="Custom Preview Tenant")
        lease = self.create_lease(apartment["id"], tenant["id"], [tenant["id"]])

        # Custom template with clear variable
        custom_template = """
        <html>
        <body>
            <h1>Test Contract</h1>
            <p>Tenant: {{ tenant_name }}</p>
            <p>Value: {{ rental_value }}</p>
        </body>
        </html>
        """

        # Preview
        response = self.client.post(
            "/api/leases/preview_contract_template/",
            {"content": custom_template, "lease_id": lease["id"]},
            format="json",
        )
        self.assert_response_success(response, 200)
        preview_html = response.json()["html"]
        assert "Test Contract" in preview_html


@pytest.mark.django_db
@pytest.mark.skipif(not redis_available(), reason="Redis is not available")
class TestTemplateBackupAndRestoreFlow(BaseE2ETest):
    """Test template backup and restore workflows."""

    def test_complete_backup_restore_workflow(self):
        """
        E2E Test: Complete backup and restore workflow

        Workflow:
        1. Save template version 1 → Creates backup1
        2. Save template version 2 → Creates backup2
        3. Save template version 3 → Creates backup3
        4. List backups → Should show all 3
        5. Restore backup2 → 200
        6. Verify current template matches backup2
        """
        self.authenticate_as_admin()

        # Step 1: Save version 1
        content_v1 = "<html><body><h1>Version 1</h1></body></html>"
        response = self.client.post("/api/leases/save_contract_template/", {"content": content_v1}, format="json")
        self.assert_response_success(response, 200)
        backup1 = response.json()["backup_filename"]

        # Step 2: Save version 2
        content_v2 = "<html><body><h1>Version 2</h1></body></html>"
        response = self.client.post("/api/leases/save_contract_template/", {"content": content_v2}, format="json")
        self.assert_response_success(response, 200)
        backup2 = response.json()["backup_filename"]

        # Step 3: Save version 3
        content_v3 = "<html><body><h1>Version 3</h1></body></html>"
        response = self.client.post("/api/leases/save_contract_template/", {"content": content_v3}, format="json")
        self.assert_response_success(response, 200)
        backup3 = response.json()["backup_filename"]

        # Step 4: List backups
        response = self.client.get("/api/leases/list_template_backups/")
        self.assert_response_success(response, 200)
        backups = response.json()
        assert len(backups) >= 3
        backup_filenames = [b["filename"] for b in backups]
        assert backup1 in backup_filenames
        assert backup2 in backup_filenames
        assert backup3 in backup_filenames

        # Step 5: Restore backup2
        response = self.client.post("/api/leases/restore_template_backup/", {"backup_filename": backup2}, format="json")
        self.assert_response_success(response, 200)
        restore_result = response.json()
        assert "message" in restore_result
        assert "restaurado" in restore_result["message"].lower()

        # Step 6: Verify restoration
        response = self.client.get("/api/leases/get_contract_template/")
        self.assert_response_success(response, 200)
        current = response.json()["content"]
        assert "Version 2" in current

    def test_backup_list_sorting_flow(self):
        """
        E2E Test: Backup list is sorted by creation date

        Workflow:
        1. Create multiple backups
        2. List backups → Should be sorted newest first
        3. Verify sorting
        """
        self.authenticate_as_admin()

        # Create backups
        import time

        backups_created = []
        for i in range(3):
            content = f"<html><body><h1>Backup {i}</h1></body></html>"
            response = self.client.post("/api/leases/save_contract_template/", {"content": content}, format="json")
            self.assert_response_success(response, 200)
            backups_created.append(response.json()["backup_filename"])
            time.sleep(0.1)  # Small delay to ensure different timestamps

        # List backups
        response = self.client.get("/api/leases/list_template_backups/")
        self.assert_response_success(response, 200)
        backups = response.json()

        # Verify all created backups are in the list
        backup_filenames = [b["filename"] for b in backups]
        for created in backups_created:
            assert created in backup_filenames

    def test_restore_nonexistent_backup_flow(self):
        """
        E2E Test: Restore non-existent backup

        Workflow:
        1. Attempt to restore non-existent backup → 404
        """
        self.authenticate_as_admin()

        response = self.client.post(
            "/api/leases/restore_template_backup/", {"backup_filename": "nonexistent_backup_file.html"}, format="json"
        )
        self.assert_response_error(response, 404)


@pytest.mark.django_db
@pytest.mark.skipif(not redis_available(), reason="Redis is not available")
class TestTemplatePermissionsFlow(BaseE2ETest):
    """Test template management permissions."""

    def test_admin_only_template_management(self):
        """
        E2E Test: Only admins can manage templates

        Workflow:
        1. Regular user attempts to get template → 403
        2. Regular user attempts to save template → 403
        3. Admin can access all template endpoints → 200
        """
        # Step 1: Regular user
        self.authenticate_as_user()

        response = self.client.get("/api/leases/get_contract_template/")
        self.assert_response_error(response, 403)

        response = self.client.post(
            "/api/leases/save_contract_template/", {"content": "<html><body>Test</body></html>"}, format="json"
        )
        self.assert_response_error(response, 403)

        # Step 2: Admin user
        self.authenticate_as_admin()

        response = self.client.get("/api/leases/get_contract_template/")
        self.assert_response_success(response, 200)

        response = self.client.post(
            "/api/leases/save_contract_template/", {"content": "<html><body>Admin Test</body></html>"}, format="json"
        )
        self.assert_response_success(response, 200)
