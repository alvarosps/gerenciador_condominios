"""Tests for the global DRF exception handler (core/exceptions.py)."""

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status

from core.exceptions import custom_exception_handler


@pytest.mark.unit
class TestCustomExceptionHandler:
    def test_django_validation_error_with_message_dict_returns_400_field_shape(self) -> None:
        exc = DjangoValidationError({"marital_status": ["Value 'Solteira' is not a valid choice."]})
        response = custom_exception_handler(exc, {})
        assert response is not None
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "marital_status" in response.data

    def test_django_validation_error_plain_message_returns_400_non_field_errors(self) -> None:
        exc = DjangoValidationError("CPF inválido")
        response = custom_exception_handler(exc, {})
        assert response is not None
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "non_field_errors" in response.data

    def test_http404_still_maps_to_404(self) -> None:
        response = custom_exception_handler(Http404(), {})
        assert response is not None
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unknown_exception_returns_none(self) -> None:
        assert custom_exception_handler(RuntimeError("boom"), {}) is None
