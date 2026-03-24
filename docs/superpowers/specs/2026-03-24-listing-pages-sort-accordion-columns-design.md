# Listing Pages: Sort, Accordion por Prédio, Colunas de Inquilinos

**Data:** 2026-03-24
**Status:** Aprovado

## Objetivo

Melhorar as páginas de listagem (Apartamentos, Inquilinos, Locações) com:
1. Ordenação clicável por coluna com setas duplas ▲▼
2. Agrupamento por prédio via accordions (Apartamentos e Locações)
3. Reestruturação das colunas da página de Inquilinos

## Decisões de Design

| Decisão | Escolha |
|---|---|
| Estilo do sort | Setas duplas ▲▼ separadas — clicar individualmente em cada seta |
| Filtros nos accordions | Dentro de cada accordion (independentes por prédio) |
| Estado padrão dos accordions | Fechados |
| Botão "Ver contrato" (inquilinos) | Navega para `/leases` |
| Filtros removidos (inquilinos) | Dependentes, Móveis |

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

A página chama `useActiveLeases()` (hook já existente em `use-leases.ts` que wrapa `useLeases({ is_active: true })`). Com `useMemo`, cria `Map<number, Lease>`:

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

### Navegação "Ver contrato"
- `router.push('/leases')` usando `useRouter` do Next.js
- Navega para a página de locações (onde o usuário pode encontrar a locação no accordion do prédio correspondente)

### Arquivos afetados
- `app/(dashboard)/tenants/page.tsx` — remover colunas/filtros, adicionar novas colunas, buscar leases ativos
- `lib/hooks/use-export.ts` — remover de `tenantExportColumns`: email, profession, marital_status, dependents count, furnitures count. Manter apenas: name, cpf_cnpj, phone, is_company. Não adicionar colunas de lease ao export (dados derivados de outro recurso, complexidade desnecessária)

---

## Resumo de arquivos afetados

| Arquivo | Tipo de mudança |
|---|---|
| `components/tables/data-table.tsx` | Adicionar lógica de sort + setas ▲▼ |
| `app/(dashboard)/apartments/page.tsx` | Refatorar para accordions por prédio |
| `app/(dashboard)/tenants/page.tsx` | Remover/adicionar colunas e filtros |
| `app/(dashboard)/leases/page.tsx` | Refatorar para accordions por prédio |
| `app/(dashboard)/leases/_components/lease-filters.tsx` | **Deletar** — filtros passam a ser inline nos accordions |
| `app/(dashboard)/leases/_components/lease-table-columns.tsx` | Adicionar sorters + coluna "Prédio / Apto" → "Apto" |
| `lib/hooks/use-export.ts` | Remover colunas deletadas de `tenantExportColumns` |

## Fora de escopo
- Mudanças no backend (sorting é 100% client-side — dados já vêm completos com `page_size=10000`)
- Página de Móveis (não mencionada nos requisitos)
- Multi-column sort (sort por apenas uma coluna de cada vez)
