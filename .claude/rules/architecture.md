# Architecture Rules

## Backend Layers
- **Models** (`core/models.py`): Data + validation only. No business logic.
- **Serializers** (`core/serializers.py`): Validation + transformation. Dual pattern: nested read, `_id` write.
- **Views** (`core/views.py`, `core/viewsets/`): HTTP handling only. Delegate to services.
- **Services** (`core/services/`): All business logic lives here. Services are stateless functions.
- **Validators** (`core/validators/`): Reusable field validators (CPF, CNPJ).

## Dependency Direction
- Views → Services → Models (never the reverse)
- Serializers → Models (never Services)
- Services can call other Services
- Models never import from views, serializers, or services

## Cache Layer
- `core/cache.py`: CacheManager + @cache_result decorator
- `core/signals.py`: Automatic invalidation on model save/delete
- When adding new models: add signal handlers for cache invalidation

## Frontend Layers
- **Pages** (`app/`): Route components, use hooks, minimal logic
- **Components** (`components/`): Reusable UI, receive props, no direct API calls
- **Hooks** (`lib/api/hooks/`): TanStack Query hooks for all API communication
- **Schemas** (`lib/schemas/`): Zod schemas for form validation
- **Store** (`store/`): Zustand for client-only state (auth)

## File Placement
- New API endpoints: add to `core/views.py` or create new viewset in `core/viewsets/`
- New business logic: create/extend service in `core/services/`
- New frontend pages: `app/(dashboard)/<resource>/page.tsx`
- New hooks: `lib/api/hooks/use-<resource>.ts`
- New schemas: `lib/schemas/<resource>.ts`
