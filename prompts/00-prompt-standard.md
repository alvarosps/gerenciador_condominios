# Padrão de Prompts — Módulo Financeiro

## Princípios de Context Engineering

### 1. Contexto Mínimo Relevante
Cada sessão carrega **apenas** o contexto necessário para aquela fase:
- O design doc é referenciado via `@docs/plans/2026-03-21-financial-module-design.md`, nunca colado
- Exemplares de padrão são referenciados por arquivo + linhas exatas
- Estado da sessão anterior é lido de `prompts/SESSION_STATE.md`

### 2. Exemplar > Descrição
Em vez de descrever convenções, cada prompt aponta para um **exemplar concreto** no código existente:
- "Siga o padrão de `BuildingSerializer` em `core/serializers.py:8-11`"
- Isso é mais preciso e consome menos contexto do que explicar o padrão

### 3. TDD Rigoroso
Toda sessão segue o ciclo:
1. **Red**: Escrever testes que falham (baseados na especificação)
2. **Green**: Implementar o mínimo para os testes passarem
3. **Refactor**: Limpar sem alterar comportamento
4. **Verify**: Rodar toda a suite de testes para garantir zero regressão

### 4. Escopo Fechado
Cada sessão tem:
- Lista explícita de **arquivos a criar**
- Lista explícita de **arquivos a modificar**
- Lista explícita de **o que NÃO fazer**
- Critérios de aceite binários (passou/não passou)

### 5. Handoff entre Sessões
Ao final de cada sessão:
1. Rodar todos os testes (`pytest` + `npm run test` se frontend)
2. Atualizar `prompts/SESSION_STATE.md` com progresso
3. Commitar com mensagem descritiva
4. A próxima sessão começa lendo o SESSION_STATE.md

---

## Referência de Exemplares (Line Ranges)

### Backend — Models (`core/models.py`)
| Padrão | Linhas | Uso |
|--------|--------|-----|
| SoftDeleteManager | 31-49 | Manager customizado para queries |
| AuditMixin | 51-99 | Mixin de auditoria (created/updated by/at) |
| SoftDeleteMixin | 101-171 | Mixin de soft delete (is_deleted, restore) |
| Building (model simples) | 178-202 | Padrão para models com campos básicos |
| Furniture (model M2M) | 204-226 | Padrão para models usados como M2M |
| Lease (model complexo) | 453-570 | Padrão com validators, clean(), indexes |

### Backend — Serializers (`core/serializers.py`)
| Padrão | Linhas | Uso |
|--------|--------|-----|
| BuildingSerializer (simples) | 8-11 | ModelSerializer básico |
| ApartmentSerializer (nested + sync) | 20-89 | Nested read + ID write + create/update custom |
| TenantSerializer (dependents) | 107-199 | Nested create/update com related objects |
| LeaseSerializer (complexo) | 201-279 | Múltiplos nested + cross-model sync |

### Backend — Views (`core/views.py`)
| Padrão | Linhas | Uso |
|--------|--------|-----|
| BuildingViewSet (simples) | 19-46 | CRUD básico com prefetch |
| ApartmentViewSet (filtros) | 65-127 | ViewSet com query param filters |
| LeaseViewSet (custom actions) | 201-435 | ViewSet com @action decorators |
| DashboardViewSet (read-only) | 438-581 | ViewSet sem ModelViewSet, apenas @action |

### Backend — ViewSets (`core/viewsets/`)
| Padrão | Arquivo | Linhas | Uso |
|--------|---------|--------|-----|
| LandlordViewSet (singleton) | landlord_views.py | 24-83 | GET/PUT singleton pattern |

### Backend — Services (`core/services/`)
| Padrão | Arquivo | Linhas | Uso |
|--------|---------|--------|-----|
| BaseService (genérico) | base.py | 20-209 | CRUD genérico tipado |
| FeeCalculatorService (static) | fee_calculator.py | 20-197 | Service com @staticmethod |
| DashboardService (agregações) | dashboard_service.py | 30+ | Agregações Django ORM |

### Backend — Services (`finances/services/`)
| Padrão | Arquivo | Uso |
|--------|---------|-----|
| Month board service (agregação operacional multi-seção, uncached) | `condo_month_board_service.py` — `CondoMonthBoardService.build(year, month, today) -> dict` | Um serviço monta `{overdue, deferred_suspended, groups, totals, generation}` em UMA chamada — fonte única de um cockpit inteiro; consumido por `dashboard_views.py::month_board` (uncached, `IsAdminUser`) |
| Account statement service (StatCards + linhas + planos) | `account_statement_service.py` — `AccountStatementService.build(account_id, today) -> dict` | Extrato mês a mês de uma entidade agregando por dois braços de FK (`Q(fk_direta) \| Q(fk_indireta__via_relacao)`) — padrão para "saldo devedor" quando o dinheiro pode vir de duas origens |

### Backend — ViewSets (`finances/viewsets/`)
| Padrão | Arquivo | Uso |
|--------|---------|-----|
| Action de collection ANTES da rota `:id` genérica (ordering do router) | `crud_views.py` — `billing-accounts/{id}/statement` e `{id}/consolidate_debt` registrados antes do `retrieve`/`update` genérico | Evita a rota `:id` do DRF router engolir a action — mesma regra vale no MSW (`handlers.ts`) |

### Backend — URLs (`core/urls.py`)
| Padrão | Linhas | Uso |
|--------|--------|-----|
| Router registration | 8-17 | Registro de ViewSets no DefaultRouter |

### Frontend — Schemas (`frontend/lib/schemas/`)
| Padrão | Arquivo | Linhas | Uso |
|--------|---------|--------|-----|
| Schema simples | building.schema.ts | 1-18 | Zod schema com campos opcionais |
| Schema complexo | lease.schema.ts | 1-47 | Nested objects, transforms |

### Frontend — Hooks (`frontend/lib/api/hooks/`)
| Padrão | Arquivo | Linhas | Uso |
|--------|---------|--------|-----|
| CRUD hooks simples | use-buildings.ts | 1-100 | useQuery + useMutation padrão |
| CRUD hooks complexos | use-leases.ts | 1-233 | Com hooks extras para actions |
| Dashboard hooks | use-dashboard.ts | 1-167 | Hooks com staleTime/refetchInterval |

### Frontend — Pages (`frontend/app/(dashboard)/`)
| Padrão | Arquivo | Linhas | Uso |
|--------|---------|--------|-----|
| CRUD page canônica | buildings/page.tsx | 1-228 | useCrudPage + DataTable + modals |
| CRUD page complexa | leases/page.tsx | 1-250+ | Extra modals, filters, dynamic imports |
| Rota dinâmica `[id]` (primeiro precedente do dashboard) | `finances/accounts/[id]/page.tsx` | 1-177 | `'use client'` + `useParams<{id:string}>()` + guard de id inválido (empty state PT, sem redirect) + `PageHeader` + `StatCard`×N + `DataTable`; ver também `finances/accounts/[id]/__tests__/account-detail-page.test.tsx` para o padrão de mock local de `useParams`/`useRouter` |
| Cockpit sobre serviço de agregação (fonte única, sem cache) | `finances/bills/page.tsx` (S74/S75/S76) | — | `useMonthBoard(year, month)` substitui `useBills` + agrupamento client-side; seções fixas (Atrasadas) acima de um Accordion por grupo; ver `_components/overdue-section.tsx` |

### Frontend — Componentes
| Padrão | Arquivo | Linhas | Uso |
|--------|---------|--------|-----|
| Sidebar/Navegação | components/layouts/sidebar.tsx | 1-123 | ROUTES constant, menu items |
| useCrudPage hook | lib/hooks/use-crud-page.ts | 1-200+ | State management para CRUD pages |
| Constantes | lib/utils/constants.ts | 1-42 | ROUTES, PAGINATION, etc. |
| Popover-em-célula (edição inline sem célula editável genérica) | `finances/bills/_components/bill-inline-edit.tsx` (`DueDatePopover`/`AmountPopover`), `bill-pay-popover.tsx` | — | Reusa `components/ui/popover.tsx` dentro do `render` da coluna do `DataTable` — não criar um tipo de célula editável genérica no `DataTable` |
| Toast acionável de erro de mutação (mês fechado → link) | `lib/utils/error-handler.ts` — `showFinanceMutationError(error, fallback, goToMonthClose)` | — | Detecção por substring (`/fechad/i`) sobre `getErrorMessage`, 400 apenas; `toast.error(msg, { action: { label, onClick } })` (sonner) — precedente único, todo `onError` de mutação do cockpit delega a este helper |

---

## Estrutura de Cada Prompt de Sessão

```markdown
## Contexto
- Ler design doc: @docs/plans/2026-03-21-financial-module-design.md
- Ler estado: @prompts/SESSION_STATE.md
- Ler exemplares: [lista de arquivos específicos]

## Escopo
- Arquivos a criar: [lista]
- Arquivos a modificar: [lista]

## Especificação
[O que implementar com interfaces/assinaturas]

## TDD
1. Criar arquivo de teste: [caminho]
2. Escrever testes que cobrem: [lista de cenários]
3. Rodar testes (devem falhar): pytest [caminho]
4. Implementar: [o que implementar]
5. Rodar testes (devem passar): pytest [caminho]
6. Rodar suite completa: pytest

## Constraints
- [O que NÃO fazer]

## Critérios de Aceite
- [ ] [lista binária]

## Handoff
1. Rodar pytest (100% passando)
2. Atualizar prompts/SESSION_STATE.md
3. Commitar
```

---

## Como Usar

1. Abra uma nova sessão do Claude Code
2. Cole/referencie o prompt da sessão atual (ex: `prompts/01-backend-models.md`)
3. O prompt instrui o Claude a ler os arquivos necessários
4. Siga o fluxo TDD descrito no prompt
5. Ao final, atualize o SESSION_STATE.md e commite
6. Na próxima sessão, o Claude lê o SESSION_STATE.md para contexto do que já foi feito
