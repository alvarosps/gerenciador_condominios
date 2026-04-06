---
paths:
  - "core/views.py"
  - "core/viewsets/**"
  - "core/serializers.py"
  - "core/urls.py"
---

# API Design Rules

## Serializer Pattern
- Read: nested serializers for FK/M2M (`building = BuildingSerializer(read_only=True)`)
- Write: `_id` fields with PrimaryKeyRelatedField (`building_id = PrimaryKeyRelatedField(write_only=True, source='building')`)
- M2M write: `_ids` suffix (`furniture_ids`, `tenant_ids`)

## ViewSet Pattern
- Use ModelViewSet for standard CRUD
- Custom actions: `@action(detail=True)` for instance actions, `@action(detail=False)` for collection
- Business logic in services, not in viewsets

## Response Format
- List endpoints: paginated with `results` array
- Error format: DRF standard (`detail`, `non_field_errors`, field-level errors)
- Export endpoints: `/export/excel/` and `/export/csv/` on each resource

## URL Naming
- Resources are plural: `buildings/`, `apartments/`, `tenants/`, `leases/`, `furnitures/`
- Actions use underscores: `generate_contract/`, `calculate_late_fee/`
