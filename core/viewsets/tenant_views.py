"""
Tenant portal API views.

Provides all endpoints for the tenant mobile experience:
- Profile and lease data
- Contract PDF download
- Rent payment history
- Rent adjustment history
- PIX code generation
- Payment proof upload and status
- Due date change fee simulation
- In-app notifications
"""

import logging
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponseBase
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from core.models import (
    FinancialSettings,
    Landlord,
    Lease,
    Notification,
    PaymentProof,
    RentAdjustment,
    RentPayment,
    Tenant,
)
from core.pagination import CustomPageNumberPagination
from core.permissions import HasActiveLease, IsTenantUser
from core.serializers import (
    NotificationSerializer,
    PaymentProofSerializer,
    RentAdjustmentSerializer,
    RentPaymentSerializer,
)
from core.services.fee_calculator import FeeCalculatorService
from core.services.notification_service import notify_new_proof
from core.services.pix_service import generate_pix_payload

logger = logging.getLogger(__name__)

_MAX_DUE_DAY = 31
_MIN_DUE_DAY = 1


def _get_tenant(request: Request) -> Tenant | None:
    """Return the Tenant associated with the current user, or None."""
    return getattr(request.user, "tenant_profile", None)


def _get_active_lease(tenant: Tenant) -> Lease | None:
    """Return the active (non-deleted) lease for a tenant, or None."""
    return (
        tenant.leases_responsible.filter(is_deleted=False)
        .select_related("apartment", "apartment__building", "apartment__owner")
        .first()
    )


class TenantViewSet(viewsets.ViewSet):
    """
    ViewSet for the tenant mobile portal.

    All endpoints require IsTenantUser permission — admin users cannot
    access these endpoints. Write endpoints additionally require HasActiveLease.

    URL prefix: /api/tenant/
    """

    permission_classes = [IsTenantUser]

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request: Request) -> Response:
        """
        GET /api/tenant/me/

        Returns the authenticated tenant's profile data along with their
        current lease and apartment information.
        """
        tenant = _get_tenant(request)
        if tenant is None:
            return Response(
                {"detail": "Perfil de inquilino não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        lease = _get_active_lease(tenant)
        data = {
            "id": tenant.pk,
            "name": tenant.name,
            "cpf_cnpj": tenant.cpf_cnpj,
            "is_company": tenant.is_company,
            "rg": tenant.rg,
            "phone": tenant.phone,
            "marital_status": tenant.marital_status,
            "profession": tenant.profession,
            "due_day": tenant.due_day,
            "warning_count": tenant.warning_count,
            "dependents": list(tenant.dependents.values("id", "name", "phone", "cpf_cnpj")),
        }
        if lease:
            apt = lease.apartment
            data["lease"] = {
                "id": lease.pk,
                "start_date": lease.start_date,
                "validity_months": lease.validity_months,
                "rental_value": str(lease.rental_value),
                "pending_rental_value": (
                    str(lease.pending_rental_value) if lease.pending_rental_value else None
                ),
                "pending_rental_value_date": lease.pending_rental_value_date,
                "number_of_tenants": lease.number_of_tenants,
                "contract_generated": lease.contract_generated,
            }
            data["apartment"] = {
                "id": apt.pk,
                "number": apt.number,
                "building_name": apt.building.name,
                "building_address": apt.building.street_number,
            }
        return Response(data)

    @action(detail=False, methods=["get"], url_path="contract")
    def contract(self, request: Request) -> HttpResponseBase:
        """
        GET /api/tenant/contract/

        Returns the tenant's lease contract PDF as a file download.
        """
        tenant = _get_tenant(request)
        if tenant is None:
            return Response(
                {"detail": "Perfil de inquilino não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        lease = _get_active_lease(tenant)
        if lease is None:
            return Response(
                {"detail": "Nenhuma locação ativa encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not lease.contract_generated:
            return Response(
                {"detail": "Contrato ainda não foi gerado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        apt = lease.apartment
        pdf_path = (
            Path(settings.BASE_DIR)
            / "contracts"
            / str(apt.building.street_number)
            / f"contract_apto_{apt.number}_{lease.pk}.pdf"
        )

        if not pdf_path.is_file():
            return Response(
                {"detail": "Arquivo do contrato não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return FileResponse(
            pdf_path.open("rb"),
            content_type="application/pdf",
            as_attachment=False,
            filename=f"contrato_apto_{apt.number}.pdf",
        )

    @action(detail=False, methods=["get"], url_path="payments")
    def payments(self, request: Request) -> Response:
        """
        GET /api/tenant/payments/

        Returns a paginated list of rent payments for the tenant's active lease.
        """
        tenant = _get_tenant(request)
        if tenant is None:
            return Response(
                {"detail": "Perfil de inquilino não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        lease = _get_active_lease(tenant)
        if lease is None:
            return Response(
                {"detail": "Nenhuma locação ativa encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        queryset = RentPayment.objects.filter(lease=lease).order_by("-reference_month")

        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = RentPaymentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="rent-adjustments")
    def rent_adjustments(self, request: Request) -> Response:
        """
        GET /api/tenant/rent-adjustments/

        Returns a list of rent adjustments for the tenant's active lease.
        """
        tenant = _get_tenant(request)
        if tenant is None:
            return Response(
                {"detail": "Perfil de inquilino não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        lease = _get_active_lease(tenant)
        if lease is None:
            return Response(
                {"detail": "Nenhuma locação ativa encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        queryset = RentAdjustment.objects.filter(lease=lease).order_by("-adjustment_date")
        serializer = RentAdjustmentSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="payments/pix",
        permission_classes=[IsTenantUser, HasActiveLease],
    )
    def payments_pix(self, request: Request) -> Response:
        """
        POST /api/tenant/payments/pix/

        Generates a PIX copy-and-paste code for the tenant's current rent.

        Request body:
            amount (optional): Override the amount. Defaults to rental_value.
            description (optional): Payment description.
        """
        tenant = _get_tenant(request)
        if tenant is None:
            return Response(
                {"detail": "Perfil de inquilino não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        lease = _get_active_lease(tenant)
        if lease is None:
            return Response(
                {"detail": "Nenhuma locação ativa encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        apt = lease.apartment

        # Determine PIX key: owner's key (kitnet) or default (condomínio)
        pix_key = ""
        pix_key_type = ""
        merchant_name = "Condomínio"

        if apt.owner and apt.owner.pix_key:
            pix_key = apt.owner.pix_key
            pix_key_type = apt.owner.pix_key_type
            merchant_name = apt.owner.name
        else:
            settings_obj = FinancialSettings.objects.filter(pk=1).first()
            if settings_obj and settings_obj.default_pix_key:
                pix_key = settings_obj.default_pix_key
                pix_key_type = settings_obj.default_pix_key_type
            landlord = Landlord.get_active()
            if landlord:
                merchant_name = landlord.name

        try:
            payload = generate_pix_payload(
                pix_key=pix_key,
                pix_key_type=pix_key_type,
                amount=lease.rental_value,
                merchant_name=merchant_name,
                city="Sao Paulo",
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(payload)

    @action(
        detail=False,
        methods=["post"],
        url_path="payments/proof",
        permission_classes=[IsTenantUser, HasActiveLease],
        parser_classes=[MultiPartParser],
    )
    def payments_proof_upload(self, request: Request) -> Response:
        """
        POST /api/tenant/payments/proof/

        Upload a payment proof (image or PDF) for the tenant's current lease.

        Form fields:
            reference_month: Date string (YYYY-MM-DD, first of month)
            file: The proof file
            pix_code (optional): The PIX code used
        """
        tenant = _get_tenant(request)
        if tenant is None:
            return Response(
                {"detail": "Perfil de inquilino não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        lease = _get_active_lease(tenant)
        if lease is None:
            return Response(
                {"detail": "Nenhuma locação ativa encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PaymentProofSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        proof = serializer.save(lease=lease)
        notify_new_proof(proof)
        logger.info(
            "Payment proof uploaded for lease %s (month: %s)", lease.pk, proof.reference_month
        )

        return Response(
            PaymentProofSerializer(proof).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path=r"payments/proof/(?P<proof_id>\d+)",
    )
    def payments_proof_status(self, request: Request, proof_id: str | None = None) -> Response:
        """
        GET /api/tenant/payments/proof/<id>/

        Returns the status of a previously uploaded payment proof.
        """
        tenant = _get_tenant(request)
        if tenant is None:
            return Response(
                {"detail": "Perfil de inquilino não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        lease = _get_active_lease(tenant)
        if lease is None:
            return Response(
                {"detail": "Nenhuma locação ativa encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if proof_id is None:
            return Response(
                {"detail": "Comprovante não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            proof = PaymentProof.objects.get(pk=int(proof_id), lease=lease)
        except PaymentProof.DoesNotExist:
            return Response(
                {"detail": "Comprovante não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(PaymentProofSerializer(proof).data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="due-date/simulate",
        permission_classes=[IsTenantUser, HasActiveLease],
    )
    def due_date_simulate(self, request: Request) -> Response:
        """
        POST /api/tenant/due-date/simulate/

        Simulates the fee for changing the rent due date.

        Request body:
            new_due_day (int): Desired new due day (1-31)
        """
        tenant = _get_tenant(request)
        if tenant is None:
            return Response(
                {"detail": "Perfil de inquilino não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        lease = _get_active_lease(tenant)
        if lease is None:
            return Response(
                {"detail": "Nenhuma locação ativa encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        new_due_day_raw = request.data.get("new_due_day")
        if new_due_day_raw is None:
            return Response(
                {"detail": "Campo new_due_day é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_due_day = int(new_due_day_raw)
        except (TypeError, ValueError):
            return Response(
                {"detail": "new_due_day deve ser um número inteiro."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (_MIN_DUE_DAY <= new_due_day <= _MAX_DUE_DAY):
            return Response(
                {"detail": f"new_due_day deve ser entre {_MIN_DUE_DAY} e {_MAX_DUE_DAY}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=lease.rental_value,
            current_due_day=tenant.due_day,
            new_due_day=new_due_day,
        )

        return Response(
            {
                "current_due_day": tenant.due_day,
                "new_due_day": new_due_day,
                "days_difference": result["days_difference"],
                "daily_rate": result["daily_rate"],
                "fee": result["fee"],
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="notifications")
    def notifications(self, request: Request) -> Response:
        """
        GET /api/tenant/notifications/

        Returns a paginated list of notifications for the authenticated user.
        """
        if request.user.pk is None:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        queryset = Notification.objects.filter(recipient=request.user).order_by("-sent_at")

        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=["patch"],
        url_path=r"notifications/(?P<notification_id>\d+)/read",
    )
    def notification_mark_read(
        self, request: Request, notification_id: str | None = None
    ) -> Response:
        """
        PATCH /api/tenant/notifications/<id>/read/

        Marks a single notification as read.
        """
        if notification_id is None:
            return Response(
                {"detail": "Notificação não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if request.user.pk is None:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        try:
            notification = Notification.objects.get(pk=int(notification_id), recipient=request.user)
        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notificação não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])

        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="notifications/read-all")
    def notifications_read_all(self, request: Request) -> Response:
        """
        POST /api/tenant/notifications/read-all/

        Marks all of the user's unread notifications as read.
        """
        now = timezone.now()
        if request.user.pk is None:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        updated = Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True,
            read_at=now,
        )
        return Response({"marked_read": updated}, status=status.HTTP_200_OK)
