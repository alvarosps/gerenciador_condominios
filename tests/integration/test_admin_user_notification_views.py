"""Integration tests for admin-only viewsets: /api/admin/users/ and /api/admin/notifications/.

Real API calls through an authenticated admin client — no internal mocks. Exercises the
UserAdminSerializer create/update (password hashing) and the AdminNotificationViewSet actions.
"""

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Notification
from tests.constants import TEST_PASSWORD, TEST_PASSWORD_NEW


@pytest.mark.integration
@pytest.mark.django_db
class TestUserAdminViewSet:
    def test_create_user_with_password_hashes_it(self, authenticated_api_client):
        response = authenticated_api_client.post(
            "/api/admin/users/",
            data={
                "username": "novo_admin",
                "email": "novo@test.com",
                "password": TEST_PASSWORD,
                "is_staff": True,
            },
            format="json",
        )
        assert response.status_code == 201
        assert "password" not in response.data  # write-only
        user = User.objects.get(username="novo_admin")
        assert user.check_password(TEST_PASSWORD)
        assert user.is_staff is True

    def test_create_user_without_password(self, authenticated_api_client):
        response = authenticated_api_client.post(
            "/api/admin/users/",
            data={"username": "sem_senha", "email": "s@test.com"},
            format="json",
        )
        assert response.status_code == 201
        user = User.objects.get(username="sem_senha")
        # set_password was never called (the `if password` branch is skipped), so no hash is stored.
        assert user.password == ""

    def test_update_user_password(self, authenticated_api_client):
        target = User.objects.create_user(username="alvo", password=TEST_PASSWORD)
        response = authenticated_api_client.patch(
            f"/api/admin/users/{target.pk}/",
            data={"password": TEST_PASSWORD_NEW},
            format="json",
        )
        assert response.status_code == 200
        target.refresh_from_db()
        assert target.check_password(TEST_PASSWORD_NEW)

    def test_update_user_fields_without_password(self, authenticated_api_client):
        target = User.objects.create_user(username="alvo2", password=TEST_PASSWORD)
        response = authenticated_api_client.patch(
            f"/api/admin/users/{target.pk}/",
            data={"email": "atualizado@test.com"},
            format="json",
        )
        assert response.status_code == 200
        target.refresh_from_db()
        assert target.email == "atualizado@test.com"
        # Password unchanged because the `if password` branch was skipped.
        assert target.check_password(TEST_PASSWORD)

    def test_list_users(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/admin/users/")
        assert response.status_code == 200

    def test_non_admin_forbidden(self, regular_authenticated_api_client):
        response = regular_authenticated_api_client.get("/api/admin/users/")
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.django_db
class TestAdminNotificationViewSet:
    def test_list_notifications(self, authenticated_api_client, admin_user):
        Notification.objects.create(
            recipient=admin_user,
            type="new_proof",
            title="Novo comprovante",
            body="Inquilino enviou comprovante",
            sent_at=timezone.now(),
        )
        response = authenticated_api_client.get("/api/admin/notifications/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_mark_read(self, authenticated_api_client, admin_user):
        notif = Notification.objects.create(
            recipient=admin_user,
            type="new_proof",
            title="Test",
            body="Test",
            sent_at=timezone.now(),
        )
        response = authenticated_api_client.patch(f"/api/admin/notifications/{notif.pk}/read/")
        assert response.status_code == 200
        notif.refresh_from_db()
        assert notif.is_read is True
        assert notif.read_at is not None

    def test_mark_read_not_found(self, authenticated_api_client):
        response = authenticated_api_client.patch("/api/admin/notifications/999999/read/")
        assert response.status_code == 404

    def test_mark_all_read(self, authenticated_api_client, admin_user):
        for i in range(3):
            Notification.objects.create(
                recipient=admin_user,
                type="new_proof",
                title=f"N{i}",
                body="Test",
                sent_at=timezone.now(),
            )
        response = authenticated_api_client.post("/api/admin/notifications/read-all/")
        assert response.status_code == 200
        assert response.data["marked_read"] == 3
        assert Notification.objects.filter(recipient=admin_user, is_read=False).count() == 0
