from django.contrib import admin

from .models import Apartment, Building, Dependent, Furniture, Lease, Tenant


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
    list_display = ("id", "name", "cpf_cnpj", "phone", "is_company", "rent_due_day")
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
        "due_day",
        "rental_value",
        "contract_generated",
        "contract_signed",
    )
    list_filter = ("contract_generated", "contract_signed")
    search_fields = ("apartment__number", "responsible_tenant__name")
    filter_horizontal = ("tenants",)
