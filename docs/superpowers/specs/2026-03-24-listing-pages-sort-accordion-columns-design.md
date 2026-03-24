# Listing Pages: Sort, Accordion, Colunas, Ações de Contrato

**Data:** 2026-03-24
**Status:** Aprovado

## Objetivo

Melhorar as páginas de listagem (Apartamentos, Inquilinos, Locações) com:
1. Ordenação clicável por coluna com setas duplas ▲▼
2. Agrupamento por prédio via accordions (Apartamentos e Locações)
3. Reestruturação das colunas da página de Inquilinos
4. Ação "Encerrar contrato" na página de Locações
5. Ações "Trocar de kitnet" e "Criar contrato" na página de Inquilinos
6. Mudança de modelo: `Lease.apartment` de `OneToOneField` para `ForeignKey`

## Decisões de Design

| Decisão | Escolha |
|---|---|
| Estilo do sort | Setas duplas ▲▼ separadas — clicar individualmente em cada seta |
| Filtros nos accordions | Dentro de cada accordion (independentes por prédio) |
| Estado padrão dos accordions | Fechados |
| Botão "Ver contrato" (inquilinos) | Navega para `/leases` |
| Filtros removidos (inquilinos) | Dependentes, Móveis |
| Encerrar contrato | Soft delete do lease + reset campos + `is_rented = false` |
| Lease.apartment | `ForeignKey` + unique constraint condicional (permite histórico soft-deleted) |
| Trocar kitnet — campos do novo lease | `contract_generated`, `contract_signed`, `interfone_configured` começam `false` |

---

## 1. Sorting no DataTable

### Problema
O `DataTable` (`components/tables/data-table.tsx`) aceita `sorter` na interface `Column<T>` mas nunca renderiza indicadores visuais nem aplica a ordenação.

### Solução

**Novo estado interno no DataTable:**
- `sortKey: string | null` — key da coluna com sort ativo
- `sortDirection: 'asc' | 'desc' | null` — direção da ordenação

**Renderização do header:**
- Colunas com `sorter` definido → título + componente inline com duas setas ▲▼
- Colunas sem `sorter` → título normal (sem mudança)
- Interação:
  - Clicar ▲ → ativa sort ascendente
  - Clicar ▼ → ativa sort descendente
  - Clicar na seta já ativa → remove sort (volta ao estado natural)
- Visual:
  - Seta ativa: `text-primary`
  - Seta inativa: `text-muted-foreground opacity-30`
  - Cursor pointer nos headers sortáveis

**Aplicação do sort:**
- O array ordenado é um valor derivado via `useMemo`, **nunca** armazenado em `useState`:
  ```typescript
  const sortedData = useMemo(() => {
    if (!sortKey || !sortDirection) return dataSource;
    const sorter = columns.find((c) => c.key === sortKey)?.sorter;
    if (!sorter) return dataSource;
    return [...dataSource].sort((a, b) =>
      sortDirection === 'desc' ? -sorter(a, b) : sorter(a, b)
    );
  }, [dataSource, columns, sortKey, sortDirection]);
  ```
- `paginatedData` passa a fatiar de `sortedData` em vez de `dataSource`
- Reset para página 1 ao mudar sort

**Colunas sortáveis por página:**

| Página | Coluna | Sorter |
|---|---|---|
| Apartamentos | Apto | `a.number - b.number` |
| Apartamentos | Valor | `a.rental_value - b.rental_value` |
| Apartamentos | Status | `Number(a.is_rented) - Number(b.is_rented)` |
| Inquilinos | Nome / Razão Social | `a.name.localeCompare(b.name)` |
| Locações | Inquilino Responsável | `(a.responsible_tenant?.name ?? '').localeCompare(b.responsible_tenant?.name ?? '')` |
| Locações | Período | `new Date(a.start_date).getTime() - new Date(b.start_date).getTime()` (já existe) |
| Locações | Status | Prioridade numérica via `color` de `getLeaseStatus()`: `{ red: 0, orange: 1, green: 2, blue: 3 }` (Expirado → Expirando → Ativo → Futuro) |
| Locações | Período Mínimo | `const val = status.completed ? -1 : status.monthsRemaining; return aVal - bVal;` (completed primeiro, depois por meses restantes crescente) |
| Locações | Vencimento | `(a.responsible_tenant?.due_day ?? 0) - (b.responsible_tenant?.due_day ?? 0)` (já existe) |
| Locações | Contrato | Prioridade numérica: `{ signed: 0, generated: 1, pending: 2 }` — `contract_signed` → 0, `contract_generated && !contract_signed` → 1, else → 2 |

### Arquivos afetados
- `components/tables/data-table.tsx` — adicionar lógica de sort e renderização de setas
- `app/(dashboard)/leases/_components/lease-table-columns.tsx` — adicionar sorters nas colunas Status, Período Mínimo, Inquilino Responsável, Contrato

---

## 2. Accordions por Prédio (Apartamentos + Locações)

### Conceito
Nas páginas de Apartamentos e Locações, substituir a lista flat por accordions — um por prédio. Cada accordion contém seus próprios filtros e tabela, com estado isolado.

### Componente: nenhum componente genérico compartilhado
Após análise, cada página tem filtros e colunas suficientemente diferentes. Um componente genérico `BuildingAccordionList` adicionaria complexidade desnecessária (generics, render props) para apenas 2 consumidores. Seguindo KISS/YAGNI, cada página implementa seus accordions diretamente usando o `Accordion` do shadcn/ui.

### Página de Apartamentos

**Layout:**
```
Header (título + botões Exportar/Novo)
Bulk selection banner (se houver seleção)
Accordion "Prédio A — Nº 123" (fechado por padrão)
  ├── Filtros: Status, Valor Mín, Valor Máx, [Limpar Filtros]
  └── DataTable: Apto↕, Valor↕, Taxa Limpeza, Status↕, Inquilinos, Móveis, Ações
Accordion "Prédio B — Nº 456" (fechado por padrão)
  ├── Filtros: Status, Valor Mín, Valor Máx, [Limpar Filtros]
  └── DataTable: Apto↕, Valor↕, Taxa Limpeza, Status↕, Inquilinos, Móveis, Ações
```

**Mudanças:**
- Remove o filtro de prédio (redundante — dados já separados por accordion)
- Remove a coluna "Prédio" da tabela (redundante — prédio está no título do accordion)
- Agrupa apartamentos por `building_id` via `useMemo` → `Map<number, Apartment[]>`
- Estado de filtros: `Record<number, { is_rented?: boolean; min_price?: number; max_price?: number }>` keyed por `building_id`
- Accordion: `type="multiple"`, `defaultValue={[]}` (ambos fechados)
- Título do accordion: `{building.name} — Nº {building.street_number}` + badge com count de apartamentos

**Filtragem por accordion:**
- Cada accordion aplica filtros localmente sobre os apartamentos daquele prédio
- Usa `useMemo` para filtrar: `groupedApartments.get(buildingId).filter(...)` baseado no estado de filtros daquele building_id

### Página de Locações

**Layout:**
```
Header (título + botões Exportar/Nova Locação)
Bulk selection banner (se houver seleção)
Accordion "Prédio A — Nº 123" (fechado por padrão)
  ├── Filtros: Inquilino Responsável, Status (Ativo/Expirado/Expirando), [Limpar Filtros]
  └── DataTable: Apto, Inquilino Responsável↕, Período↕, Status↕, Período Mínimo↕, Valor, Vencimento↕, Contrato↕, Ações
Accordion "Prédio B — Nº 456" (fechado por padrão)
  ├── Filtros: ...
  └── DataTable: ...
```

**Mudanças:**
- Remove filtro de apartamento (implícito no accordion)
- Coluna "Prédio / Apto" → "Apto" (só número do apartamento)
- Agrupa leases por `apartment.building.id` via `useMemo` → `Map<number, Lease[]>`
- Estado de filtros: `Record<number, { responsible_tenant_id?: number; is_active?: boolean; is_expired?: boolean; expiring_soon?: boolean }>` keyed por `building_id`
- O filtro de Inquilino Responsável dentro de cada accordion mostra apenas os tenants com lease naquele prédio
- `LeaseFiltersCard` é substituído por filtros inline dentro de cada accordion

### Bulk operations e export
- O mesmo `crud.bulkOps.rowSelection` é passado a **todos** os `DataTable` dos accordions
- "Select all" dentro de um accordion seleciona apenas as linhas daquele accordion (comportamento natural do DataTable, que opera sobre seu próprio `dataSource`)
- A seleção é acumulativa — selecionar linhas no accordion A e depois no accordion B mantém ambas selecionadas
- Export e bulk delete operam sobre `selectedRowKeys` acumuladas de todos os accordions
- O banner de seleção e os botões de bulk ficam no nível da página (acima dos accordions)

### Leases sem building (edge case)
Na prática, todas as leases têm apartment com building. Como guarda defensiva: leases onde `apartment?.building?.id` é `undefined` são ignoradas (não aparecem em nenhum accordion). Isso evita crashes sem precisar de um accordion catch-all para um cenário que não ocorre na prática.

### Arquivos afetados
- `app/(dashboard)/apartments/page.tsx` — refatorar para accordions
- `app/(dashboard)/leases/page.tsx` — refatorar para accordions
- `app/(dashboard)/leases/_components/lease-filters.tsx` — **deletar** este componente; filtros passam a ser inline dentro de cada accordion na `leases/page.tsx`
- `app/(dashboard)/leases/_components/lease-table-columns.tsx` — coluna "Prédio / Apto" → "Apto", remover coluna "Prédio" do apartments

---

## 3. Colunas da Página de Inquilinos

### Colunas removidas
| Coluna | Key |
|---|---|
| Email | `email` |
| Profissão | `profession` |
| Estado Civil | `marital_status` |
| Dependentes | `dependents` |
| Móveis | `furnitures` |

### Filtros removidos
| Filtro | Key |
|---|---|
| Dependentes | `has_dependents` |
| Móveis | `has_furniture` |

**Filtros mantidos:** Busca por Nome/CPF/CNPJ (`search`), Tipo (`is_company`)

### Colunas adicionadas

| Coluna | Dado | Visual | Sem lease ativa |
|---|---|---|---|
| Contrato Ativo | lease ativa existe? | Badge verde "Sim" / cinza "Não" | Badge cinza "Não" |
| Contrato Assinado | `lease.contract_signed` | Badge azul "Sim" / amarelo "Não" | "—" |
| Interfone | `lease.interfone_configured` | Badge verde "Configurado" / amarelo "Pendente" | "—" |
| Contrato | ação de navegação | Botão "Ver" → navega para `/leases` | "—" |

### Layout final das colunas (ordem)
1. Nome / Razão Social (sort ▲▼)
2. CPF / CNPJ
3. Telefone
4. Contrato Ativo
5. Contrato Assinado
6. Interfone
7. Contrato (botão Ver)
8. Ações (Editar, Excluir)

### Obtenção dos dados de lease

A página chama `useLeases()` (sem filtros — retorna todos os leases não-deletados, incluindo expirados). Com `useMemo`, cria `Map<number, Lease>`:

**Loading state:** As colunas de lease mostram um skeleton/shimmer enquanto `activeLeases` está carregando (`isLoading` do hook). Não bloquear a renderização dos dados de tenant — mostrar a tabela com as colunas de tenant preenchidas e as colunas de lease com loading indicator até o segundo fetch resolver.

```typescript
const leaseByTenantId = useMemo(() => {
  const map = new Map<number, Lease>();
  activeLeases?.forEach((lease) => {
    // Mapear responsible_tenant
    if (lease.responsible_tenant?.id) {
      map.set(lease.responsible_tenant.id, lease);
    }
    // Mapear todos os tenants da lease
    lease.tenants?.forEach((tenant) => {
      if (tenant.id && !map.has(tenant.id)) {
        map.set(tenant.id, lease);
      }
    });
  });
  return map;
}, [activeLeases]);
```

As colunas de lease acessam o dado via `leaseByTenantId.get(record.id)`. Nota: `record.id` é `number | undefined` no schema Zod — adicionar null guard no call site: `const lease = record.id !== undefined ? leaseByTenantId.get(record.id) : undefined`.

### Definição de "contrato ativo" para esta página
A coluna "Contrato Ativo" usa leases **não-deletados** (não `is_active` baseado em data). Usa `useLeases()` sem filtro de `is_active`, filtrando apenas por `is_deleted = false` (que o `SoftDeleteManager` faz automaticamente). Isso significa:
- Tenant com lease não-deletado mas expirado → "Contrato Ativo: Sim" (o contrato existe, só está vencido — precisa ser encerrado explicitamente)
- Tenant sem lease ou só com leases deletados → "Contrato Ativo: Não"

Essa semântica é intencional: um lease expirado ainda é um contrato "existente" que precisa de ação (encerrar ou renovar), não deve ser tratado como inexistente.

### Navegação "Ver contrato"
- `router.push('/leases')` usando `useRouter` do Next.js
- Navega para a página de locações (onde o usuário pode encontrar a locação no accordion do prédio correspondente)

### Arquivos afetados
- `app/(dashboard)/tenants/page.tsx` — remover colunas/filtros, adicionar novas colunas, buscar leases ativos
- `lib/hooks/use-export.ts` — remover de `tenantExportColumns`: email, profession, marital_status, dependents count, furnitures count. Manter apenas: name, cpf_cnpj, phone, is_company. Não adicionar colunas de lease ao export (dados derivados de outro recurso, complexidade desnecessária)

---

## 4. Mudança de Modelo: Lease.apartment OneToOneField → ForeignKey

### Problema
`Lease.apartment` é `OneToOneField(Apartment)`. Isso impede soft delete funcional — ao encerrar um contrato (soft delete), o constraint do banco impede criar um novo lease para o mesmo apartment, mesmo que o antigo esteja marcado como `is_deleted = True`.

### Solução

**Mudança no model:**
```python
# core/models.py — Lease
# ANTES:
apartment = models.OneToOneField(Apartment, on_delete=models.CASCADE, related_name="lease")

# DEPOIS:
apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name="leases")

class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["apartment"],
            condition=models.Q(is_deleted=False),
            name="unique_active_lease_per_apartment",
        )
    ]
```

**O que isso permite:**
- Múltiplos leases por apartment no banco (histórico de contratos anteriores)
- Apenas **um lease ativo** (não-deletado) por apartment, enforced no banco
- Soft delete funciona: ao encerrar, `is_deleted = True` libera o apartment para novo lease
- Reversibilidade: restaurar lease encerrado por engano (desde que não haja outro ativo no mesmo apartment)

### Impacto — `related_name` muda de `lease` para `leases`

Todos os acessos a `apartment.lease` (singular, OneToOne) precisam mudar para `apartment.leases.filter(is_deleted=False).first()` ou equivalente. Locais afetados:

**Backend:**
- `core/models.py` — qualquer referência a `apartment.lease`
- `core/serializers.py` — `ApartmentSerializer` se usar nested lease
- `core/views.py` — qualquer queryset que acesse `apartment.lease`
- `core/services/contract_service.py` — geração de PDF usa dados do lease
- `core/services/fee_calculator.py` — cálculos de multa acessam lease do apartment
- `core/signals.py` — invalidação de cache
- Testes que usem `apartment.lease`

**Frontend:**
- `lib/schemas/apartment.schema.ts` — se tiver campo `lease`, mudar para `leases` (array)
- Qualquer componente que acesse `apartment.lease`

### Atualização do signal `sync_apartment_is_rented`

O signal atual usa `is_rented = not instance.is_deleted` — funciona para OneToOne mas é **incorreto** para ForeignKey. Após a mudança, um apartment pode ter múltiplos leases (históricos soft-deleted). Se qualquer lease histórico for re-saved (ex: audit update), o signal setaria `is_rented = False` incorretamente.

**Nova lógica do signal:**
```python
# ANTES (OneToOne):
is_rented = not instance.is_deleted
Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=is_rented)

# DEPOIS (ForeignKey):
has_active_lease = Lease.objects.filter(apartment_id=instance.apartment_id).exists()
Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=has_active_lease)
```

`Lease.objects` já exclui soft-deleted via `SoftDeleteManager`, então `.exists()` retorna `True` apenas se há lease ativo.

**Também atualizar `sync_apartment_is_rented_on_delete` (hard delete):**
```python
# ANTES:
@receiver(post_delete, sender=Lease)
def sync_apartment_is_rented_on_delete(sender, instance, **kwargs):
    Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=False)

# DEPOIS:
@receiver(post_delete, sender=Lease)
def sync_apartment_is_rented_on_delete(sender, instance, **kwargs):
    has_active_lease = Lease.objects.filter(apartment_id=instance.apartment_id).exists()
    Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=has_active_lease)
```

Ambos os signals devem usar a mesma lógica query-based após a mudança para ForeignKey.

**Consequência para terminate/transfer:** Os services **não devem** setar `apartment.is_rented` manualmente. O signal cuida disso automaticamente após o soft delete e a criação do novo lease. Isso evita duplicação e race conditions.

### Migration
- Nova migration: `AlterField` de `OneToOneField` para `ForeignKey` + `AddConstraint` para unique condicional
- **Sem perda de dados** — a migration apenas relaxa o constraint

### Arquivos afetados
- `core/models.py` — mudar field + adicionar constraint
- `core/serializers.py` — atualizar related_name
- `core/views.py` — atualizar querysets
- `core/services/contract_service.py` — atualizar acesso a lease
- `core/services/fee_calculator.py` — atualizar acesso a lease
- `core/signals.py` — **atualizar lógica** do signal `sync_apartment_is_rented` (ver abaixo)
- `tests/` — atualizar testes que usam `apartment.lease`
- Nova migration em `core/migrations/`

---

## 5. Ação "Encerrar Contrato" (Página de Locações)

### Conceito
Botão "Encerrar" na coluna de ações de cada lease. Abre modal de confirmação. Ao confirmar, encerra o contrato.

### Backend — novo endpoint

**Endpoint:** `POST /api/leases/{id}/terminate/`

**Lógica (em service, não na view) — DEVE usar `@transaction.atomic`:**
1. Resetar campos do lease: `contract_generated = False`, `contract_signed = False`, `interfone_configured = False`
2. Soft delete do lease (`lease.delete()` — usa SoftDeleteMixin)
3. O signal `sync_apartment_is_rented` atualiza automaticamente `apartment.is_rented` (ver seção 4)
4. Invalidar caches relevantes (lease, apartment)

**M2M tenants:** Preservar as associações M2M no lease soft-deleted (histórico). Não limpar `lease.tenants`.

**Resposta:** `200 OK` com mensagem de sucesso

**Permissões:** Apenas `is_staff` (admin) pode encerrar contratos

### Frontend

**Botão na tabela:**
- Novo ícone na coluna de ações (ex: `XCircle` ou `Ban` do lucide-react)
- Tooltip: "Encerrar Contrato"
- Só habilitado se o lease está ativo (não expirado, não futuro)

**Modal de confirmação:**
- Título: "Encerrar Contrato"
- Descrição: "Tem certeza que deseja encerrar o contrato do Apto {number} — {building.name}? O apartamento será marcado como disponível."
- Botões: "Cancelar" / "Encerrar" (destructive)
- Loading state no botão durante request

**Após sucesso:**
- `toast.success('Contrato encerrado com sucesso')`
- Invalidar queries: leases, apartments (ambos mudam)

### Arquivos afetados
- `core/services/` — novo service function `terminate_lease(lease_id, user)`
- `core/views.py` — nova action `terminate` no `LeaseViewSet`
- `lib/api/hooks/use-leases.ts` — novo mutation `useTerminateLease()`
- `app/(dashboard)/leases/_components/lease-table-columns.tsx` — adicionar botão "Encerrar"
- `app/(dashboard)/leases/page.tsx` — adicionar modal de confirmação + handler

---

## 6. Ações "Trocar de Kitnet" e "Criar Contrato" (Página de Inquilinos)

### Conceito
Na página de Inquilinos, duas ações contextuais por inquilino:
- **"Trocar de kitnet"** — visível quando o inquilino tem contrato ativo
- **"Criar contrato"** — visível quando o inquilino **não** tem contrato ativo

Ambas abrem um modal com formulário de lease.

### 6a. "Trocar de Kitnet"

**Modal:**
- Título: "Trocar de Kitnet — {tenant.name}"
- Campos do lease form completo (mesmos do `LeaseFormModal`), **pre-preenchidos** com dados do contrato atual:
  - `apartment_id` → **vazio** (deve selecionar novo kitnet, lista mostra apenas apartamentos disponíveis)
  - `responsible_tenant_id` → pre-preenchido com o tenant atual (read-only)
  - `tenant_ids` → pre-preenchido com os tenants do contrato atual
  - `start_date` → pre-preenchido com a data de início do contrato atual (editável)
  - `validity_months` → pre-preenchido do contrato atual
  - `tag_fee` → pre-preenchido do contrato atual
  - `deposit_amount` → pre-preenchido do contrato atual
  - `cleaning_fee_paid` → `false` (novo kitnet)
  - `tag_deposit_paid` → `false` (novo kitnet)
- Todos os campos são editáveis (exceto `responsible_tenant_id`)
- Resumo do apartment selecionado (igual ao `LeaseFormModal`)

**Backend — novo endpoint:** `POST /api/leases/{id}/transfer/`

**Payload:** Campos padrão de um lease novo (usa `apartment_id` como destino, consistente com o serializer existente). O lease antigo é identificado pelo `{id}` na URL.

**Lógica (em service) — DEVE usar `@transaction.atomic`:**
1. Validar que o apartment destino (`apartment_id` do payload) não está alugado
2. Resetar campos do lease antigo: `contract_generated = False`, `contract_signed = False`, `interfone_configured = False`
3. Soft delete do lease antigo — signal atualiza `apartment_antigo.is_rented = False`
4. Criar novo lease com os dados do payload + `contract_generated = False`, `contract_signed = False`, `interfone_configured = False` — signal atualiza `apartment_novo.is_rented = True`
5. Invalidar caches

**M2M tenants do lease antigo:** Preservar (histórico). O novo lease recebe `tenant_ids` do payload.

**Resposta:** `201 Created` com o novo lease

### 6b. "Criar Contrato"

**Modal:**
- Título: "Criar Contrato — {tenant.name}"
- Campos do lease form completo (mesmos do `LeaseFormModal`):
  - `apartment_id` → **vazio** (selecionar kitnet disponível)
  - `responsible_tenant_id` → pre-preenchido com o tenant atual (read-only)
  - `tenant_ids` → pre-preenchido com `[tenant.id]`
  - `start_date` → pre-preenchido com **data de hoje** (editável)
  - `validity_months` → `12` (default)
  - `tag_fee` → `50` (default)
  - `deposit_amount` → `null`
  - `cleaning_fee_paid` → `false`
  - `tag_deposit_paid` → `false`
- Todos os campos editáveis (exceto `responsible_tenant_id`)

**Backend:** Usa o endpoint existente `POST /api/leases/` (create normal). O backend já seta `is_rented = True` no apartment ao criar lease.

### Componente compartilhado

Ambos os modais usam **o mesmo componente de formulário** — um `TenantLeaseModal` que recebe:
- `mode: 'create' | 'transfer'`
- `tenant: Tenant` (obrigatório)
- `currentLease?: Lease` (obrigatório quando `mode = 'transfer'`)

O componente reutiliza a mesma estrutura do `LeaseFormModal` existente, mas com `responsible_tenant_id` fixo e pre-preenchimento condicional.

**Campo `responsible_tenant_id` read-only:** Renderizar como texto estático (nome + CPF/CNPJ) em vez de `<Select>` — não é um select desabilitado, é um campo informativo. O valor é enviado no payload via hidden value, não via input do usuário.

### Arquivos afetados
- `core/services/` — novo service function `transfer_lease(lease_id, new_apartment_id, payload, user)`
- `core/views.py` — nova action `transfer` no `LeaseViewSet`
- `lib/api/hooks/use-leases.ts` — novo mutation `useTransferLease()`
- `app/(dashboard)/tenants/page.tsx` — adicionar botões contextuais + estado do modal
- `app/(dashboard)/tenants/_components/tenant-lease-modal.tsx` — **novo componente** (modal create/transfer)

---

## Resumo de arquivos afetados

### Frontend

| Arquivo | Tipo de mudança |
|---|---|
| `components/tables/data-table.tsx` | Adicionar lógica de sort + setas ▲▼ |
| `app/(dashboard)/apartments/page.tsx` | Refatorar para accordions por prédio |
| `app/(dashboard)/tenants/page.tsx` | Remover/adicionar colunas e filtros + botões Trocar/Criar |
| `app/(dashboard)/tenants/_components/tenant-lease-modal.tsx` | **Novo** — modal create/transfer lease |
| `app/(dashboard)/leases/page.tsx` | Refatorar para accordions + modal encerrar contrato |
| `app/(dashboard)/leases/_components/lease-filters.tsx` | **Deletar** — filtros passam a ser inline nos accordions |
| `app/(dashboard)/leases/_components/lease-table-columns.tsx` | Adicionar sorters + coluna "Apto" + botão "Encerrar" |
| `lib/api/hooks/use-leases.ts` | Novos mutations: `useTerminateLease()`, `useTransferLease()` |
| `lib/hooks/use-export.ts` | Remover colunas deletadas de `tenantExportColumns` |

### Backend

| Arquivo | Tipo de mudança |
|---|---|
| `core/models.py` | `Lease.apartment`: `OneToOneField` → `ForeignKey` + unique constraint condicional |
| `core/migrations/` | Nova migration para a mudança de field + constraint |
| `core/serializers.py` | Atualizar `related_name` de `lease` → `leases` |
| `core/views.py` | Atualizar querysets + novas actions `terminate`, `transfer` |
| `core/services/contract_service.py` | Atualizar acesso `apartment.lease` → `apartment.leases` |
| `core/services/fee_calculator.py` | Atualizar acesso `apartment.lease` → `apartment.leases` |
| `core/services/` | Novo: `terminate_lease()`, `transfer_lease()` |
| `core/signals.py` | **Atualizar lógica** `sync_apartment_is_rented` + referências related_name |
| `tests/` | Atualizar testes que usam `apartment.lease` |

## Fora de escopo
- Sorting server-side (sorting é 100% client-side — dados já vêm completos com `page_size=10000`)
- Página de Móveis (não mencionada nos requisitos)
- Multi-column sort (sort por apenas uma coluna de cada vez)
- Restauração de lease encerrado por engano (possível via admin ou futura feature, constraint permite)
