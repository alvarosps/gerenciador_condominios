from django.contrib import admin

from .models import (
    Apartment,
    Building,
    Dependent,
    DeviceToken,
    Furniture,
    Lease,
    Notification,
    PaymentProof,
    Tenant,
    WhatsAppVerification,
)


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("id", "street_number", "name", "address")
    search_fields = ("name", "address", "street_number")


@admin.register(Furniture)
class FurnitureAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "building", "is_rented", "rental_value")
    list_filter = ("building", "is_rented")
    search_fields = ("number",)
    filter_horizontal = ("furnitures",)


class DependentInline(admin.TabularInline):
    model = Dependent
    extra = 1


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "cpf_cnpj", "phone", "is_company", "due_day")
    search_fields = ("name", "cpf_cnpj")
    inlines = [DependentInline]


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "apartment",
        "responsible_tenant",
        "start_date",
        "validity_months",
        "contract_generated",
        "contract_signed",
    )
    list_filter = ("contract_generated", "contract_signed")
    search_fields = ("apartment__number", "responsible_tenant__name")
    filter_horizontal = ("tenants",)


@admin.register(WhatsAppVerification)
class WhatsAppVerificationAdmin(admin.ModelAdmin):
    list_display = ["cpf_cnpj", "phone", "is_used", "created_at", "expires_at"]
    list_filter = ["is_used"]
    search_fields = ["cpf_cnpj", "phone"]


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "is_active", "created_at"]
    list_filter = ["platform", "is_active"]


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ["lease", "reference_month", "status", "created_at"]
    list_filter = ["status"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "type", "title", "is_read", "sent_at"]
    list_filter = ["type", "is_read"]
    search_fields = ["title", "body"]
