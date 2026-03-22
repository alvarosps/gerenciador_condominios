# Condominios Manager

Sistema de gestão de imóveis para locação no Brasil — Django 5.2 + DRF (backend), Next.js 14 + React 18 (frontend), PostgreSQL 15.

## Arquitetura

```
core/                    # Django app principal (models, serializers, views, services)
core/services/           # Camada de serviços (contract, dashboard, fees, dates, templates)
core/viewsets/           # Viewsets especializados (template_views.py)
core/cache.py            # Redis caching (CacheManager, @cache_result decorator)
core/signals.py          # Django signals — invalidação automática de cache
core/validators/         # Validação CPF/CNPJ
core/middleware/         # Request/response logging, slow request warnings (>1s)
core/templates/          # Contract template HTML + backups/
contracts/               # PDFs gerados por prédio
frontend/                # Next.js 14 App Router (ver frontend/CLAUDE.md)
tests/                   # pytest test suite (ver tests/CLAUDE.md)
scripts/                 # backup_db, restore_db, deploy, generate_metrics, setup_windows
condominios_manager/     # Django settings
```

## Modelo de Dados

```
Building (street_number unique) → Apartment (number unique per building)
Apartment → Lease (OneToOne) → Tenant (responsible + M2M via LeaseTenant)
Tenant (cpf_cnpj unique) → Dependent (FK)
Furniture ↔ Apartment (M2M), Furniture ↔ Tenant (M2M)
```

**Mixins em todos os models:** `AuditMixin` (created/updated_at/by), `SoftDeleteMixin` (is_deleted, deleted_at/by)
- `Model.objects.all()` exclui deletados; `.with_deleted()` inclui; `.deleted_only()` só deletados

## Comandos

```bash
# Backend
python manage.py runserver                    # http://localhost:8000
python -m pytest                              # Todos os testes (parallel, reuse-db)
python -m pytest tests/unit/                  # Só unit tests
python -m pytest --cov=core --cov-report=html # Com coverage
pre-commit run --all-files                    # Lint/format (black, isort, flake8)

# Frontend (cd frontend/)
npm run dev                                   # http://localhost:4000
npm run build                                 # Production build
npm run test:unit                             # Vitest
npm run lint && npm run type-check            # ESLint + TypeScript
```

## Restrições Críticas

- IMPORTANT: Serializers usam padrão dual — FK read com nested (`building = BuildingSerializer(read_only=True)`), write com `_id` (`building_id = PrimaryKeyRelatedField(write_only=True, source='building')`)
- IMPORTANT: M2M segue mesmo padrão — read com nested list, write com `_ids`
- IMPORTANT: `LeaseTenant` usa `db_table='core_lease_tenant_details'` — NÃO renomear
- IMPORTANT: PDF generation requer Chrome instalado — path detection Windows-specific em `contract_service.py`
- CRITICAL: Default querysets excluem soft-deleted records — usar `with_deleted()` quando necessário
- IMPORTANT: Redis cache com invalidação automática via signals — ao mudar models/signals, verificar impacto no cache
- IMPORTANT: `CacheManager.invalidate_model(name, pk)` e `invalidate_pattern(pattern)` — cache invalida automaticamente em save/delete via signals
- Tag fee: R$50 para 1 tenant, R$80 para 2+ — lógica em `contract_service.py`
- Late fee: 5% ao dia × (rental_value ÷ 30) × days_late — lógica em `fee_calculator.py`
- Furniture no contrato = Apartment furniture − Tenant furniture
- PDFs salvos em: `contracts/{building_number}/contract_apto_{apt_number}_{lease_id}.pdf`

## Convenções

- Backend: Black (120 chars), isort (black profile), flake8 — enforced via pre-commit
- Frontend: ESLint + Prettier + TypeScript strict, husky + lint-staged (pre-commit)
- Validação brasileira: CPF (11 dígitos), CNPJ (14 dígitos), moeda R$ 1.500,00, data DD/MM/YYYY
- Estado civil: Solteiro(a), Casado(a), Divorciado(a), Viúvo(a), União Estável

## API Base: `/api/`

- CRUD para: `buildings`, `apartments`, `tenants`, `leases`, `furnitures`, `dependents`
- Auth: `/api/token/` (login), `/api/token/refresh/`, `/api/auth/me/`, `/api/auth/google/`
- Lease actions: `generate_contract/`, `calculate_late_fee/`, `change_due_date/`
- Templates: `/api/templates/current/`, `save/`, `backups/`, `restore/`, `preview/`
- Dashboard: `financial_summary/`, `late_payment_summary/`, `lease_metrics/`, `tenant_statistics/`, `building_statistics/`
- Export: `/api/{resource}/export/excel/`, `/api/{resource}/export/csv/`

## Migrations

Sequenciais: 0001 (initial) → 0008 (audit + soft delete). `LeaseTenant` usa `db_table='core_lease_tenant_details'`.

## Env Vars

- Backend `.env`: `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `GOOGLE_CLIENT_ID/SECRET`
- Frontend `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000/api`
- CORS: `localhost:4000`, `localhost:6000`
