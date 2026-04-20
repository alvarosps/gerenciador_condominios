"""
User administration viewset.

Provides CRUD for Django User accounts, restricted to admin users only.

Endpoint: /api/admin/users/
"""

from typing import Any

from django.contrib.auth.models import User
from rest_framework import serializers, viewsets

from core.permissions import IsAdminUser


class UserAdminSerializer(serializers.ModelSerializer[User]):
    """Serializer for Django User — password is write-only."""

    password = serializers.CharField(write_only=True, required=False, min_length=8)
    date_joined = serializers.DateTimeField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "password",
            "date_joined",
        ]

    def create(self, validated_data: dict[str, Any]) -> User:
        password: str = validated_data.pop("password", "")
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        password: str = validated_data.pop("password", "")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserAdminViewSet(viewsets.ModelViewSet[User]):
    """CRUD for User accounts — admin only."""

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdminUser]
