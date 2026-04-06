# Expenses Page Redesign — Design Spec

## Overview

Redesign the `/financial/expenses` page from a raw CRUD table to a monthly expense summary view with detail drill-down pages, inline with the dashboard's Resumo de Despesas section. Each expense category (person, utility, fixed) becomes a line item in the list, and clicking "Ver detalhes" opens a dedicated detail page with editable tables inside collapsible accordions.

## Pages

### 1. Expense List Page (`/financial/expenses`)

**Purpose:** Monthly view of all expense categories with payment progress tracking.

**Layout:**
- Month navigator (← | Marco de 2026 | →) with arrow icons only (no month names in buttons), total on the right
- Table with columns: Despesa, Tipo (badge), Valor, Progresso Pgto, Ações

**Data source:** Reuse `useDashboardSummary(year, month)` — the expense_summary already contains all needed data (by_person, water, electricity, iptu, internet, celular, sitio, outros_fixed, employee).

**Row types:**
- **Person (payable):** Progress bar showing paid/total from waterfall allocation. Badge "Pessoa".
- **Person (condominium):** No progress bar. Subtitle "Salário administração condomínio". Badge "Condomínio".
- **Utility (water, electricity, IPTU):** Subtitle showing prédio count. Badge "Utilidade".
- **Fixed (internet, celular, sítio, outros):** Subtitle showing item count. Badge "Fixo".
- **Employee:** Subtitle showing employee count. Badge "Salário".

**Actions column:** "Ver detalhes →" link navigating to detail page.

### 2. Expense Detail Page (`/financial/expenses/details?type=<type>&id=<id>`)

**Purpose:** Detailed breakdown of a specific expense category with editable items.

**URL params:**
- `type`: `person`, `electricity`, `water`, `iptu`, `internet`, `celular`, `sitio`, `outros_fixed`, `employee`
- `id`: Person ID (only for type=person)
- `year`, `month`: Reference period (defaults to current)

**Header:**
- Name + icon on the left
- Total value + progress bar + "Registrar Pagamento" button on the right (only for payable persons)
- Back navigation breadcrumb

**Body — Accordion sections:**
Each category of expense within this group is a collapsible accordion section. For persons: Cartões, Empréstimos, Gastos Fixos, Gastos Únicos, Descontos, Estipêndios. For utilities: by building. For fixed categories: flat list.

**Table inside each accordion:**
| Column | Description |
|--------|-------------|
| Descrição | Expense description text |
| Cartão | Credit card name (if applicable) |
| Parcela Atual | Current installment number |
| Total Parcelas | Total installment count |
| Categoria | Expense category (badge with color) |
| Subcategoria | Subcategory within category |
| Notas | Notes/observations field |
| Valor | Amount in R$ |
| Ações | Edit (pencil) + Delete (trash) buttons |

**Pagination:** Show first 10 items per accordion. "Ver todos (N itens)" button to expand.

**Edit flow:**
1. Click edit icon → opens modal/drawer
2. Modal fields: description, value (currency input), category (dropdown), subcategory (cascading dropdown filtered by selected category), notes (textarea)
3. Click "Salvar" → confirmation modal → PATCH request → refresh data
4. If category changes, subcategory clears and shows new options

**Delete flow:**
1. Click delete icon → confirmation modal with expense description
2. Confirm → DELETE request → refresh data

### 3. Dashboard Integration

**Expense modal:** Add "Ver detalhes" link at the bottom of each person/utility modal in the dashboard. Navigates to `/financial/expenses/details?type=<type>&id=<id>&year=<year>&month=<month>`.

## Backend

### New endpoint: None needed for list page

The list page reuses `GET /api/financial-dashboard/dashboard_summary/?year=&month=` which already returns all expense categories with totals, payment progress, and person details.

### New endpoint: Expense detail

`GET /api/financial-dashboard/expense_detail/?type=<type>&id=<id>&year=<year>&month=<month>`

Returns the same data structure as the dashboard's person/utility modal data, but with full details (not truncated). For persons, includes all expense installments and single expenses with their category and subcategory information. For utilities, includes building-grouped bills with debt installments.

### Existing endpoints used for mutations:
- `PATCH /api/expenses/{id}/` — update expense fields (description, category, notes, etc.)
- `DELETE /api/expenses/{id}/` — delete expense
- `PATCH /api/expense-installments/{id}/` — update installment fields
- `POST /api/person-payments/` — register payment

## Data Flow

```
Dashboard Summary API
    ├── List Page: renders table from expense_summary
    ├── Detail Page: fetches full detail via expense_detail endpoint
    └── Dashboard: renders cards + modals (existing)

Mutations (Edit/Delete):
    ├── PATCH /api/expenses/{id}/ or /api/expense-installments/{id}/
    ├── Invalidates: dashboard_summary, expense_detail queries
    └── Optimistic updates where appropriate
```

## Frontend File Structure

```
frontend/app/(dashboard)/financial/expenses/
    page.tsx                          # Rewritten: monthly expense list
    _components/
        expense-list-table.tsx        # Table component for list page
        month-navigator.tsx           # Month prev/next navigation
    details/
        page.tsx                      # Detail page (uses searchParams)
        _components/
            detail-header.tsx         # Header with progress bar + payment button
            expense-accordion.tsx     # Collapsible section with table
            expense-edit-modal.tsx    # Edit modal with category cascading
            expense-table.tsx         # Table inside accordion

frontend/lib/api/hooks/
    use-financial-dashboard.ts        # Add useExpenseDetail() hook
```

## Key Decisions

- **Query params over slugs:** Flexible, no encoding issues, Next.js native support
- **Modal for editing:** Better UX for cascading category/subcategory dropdowns than inline
- **Reuse dashboard data for list:** Single source of truth, no new endpoints for the list
- **New endpoint for detail:** Full data with categories/subcategories not available in dashboard summary
- **10-item pagination in accordions:** Performance for persons with 70+ card purchases
