# Expenses Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the raw CRUD expenses page with a monthly expense summary list + detail drill-down pages, synchronized with the dashboard.

**Architecture:** The list page reuses `useDashboardSummary` for data (single source of truth). The detail page uses a new backend endpoint that returns full expense details per category with category/subcategory info. Mutations use existing PATCH/DELETE endpoints with TanStack Query cache invalidation.

**Tech Stack:** Next.js 14 App Router, TanStack Query v5, Shadcn/ui (Dialog, Sheet), Tailwind CSS, Django REST Framework, Zod schemas.

**Spec:** `docs/superpowers/specs/2026-03-23-expenses-page-redesign.md`

---

## File Structure

### New files

```
frontend/app/(dashboard)/financial/expenses/page.tsx               # REWRITE: monthly expense list
frontend/app/(dashboard)/financial/expenses/_components/
    expense-list-table.tsx                                          # Table component
    month-navigator.tsx                                             # ← Month →  navigation
frontend/app/(dashboard)/financial/expenses/details/
    page.tsx                                                        # Detail page (searchParams)
    _components/
        detail-header.tsx                                           # Header with progress + payment btn
        expense-accordion.tsx                                       # Collapsible section with table
        expense-detail-table.tsx                                    # Table inside accordion
        expense-edit-modal.tsx                                      # Edit modal with cascading categories
core/services/financial_dashboard_service.py                        # ADD: get_expense_detail() method
core/viewsets/financial_dashboard_views.py                          # ADD: expense_detail action
frontend/lib/api/hooks/use-financial-dashboard.ts                   # ADD: useExpenseDetail() hook
```

### Modified files

```
frontend/app/(dashboard)/financial/_components/expense-summary-card.tsx   # ADD: "Ver detalhes" links in modals
frontend/app/(dashboard)/financial/expenses/_components/                  # KEEP: expense-form-modal.tsx, installments-drawer.tsx (reuse in detail page)
```

### Files to keep but no longer import from page.tsx

```
frontend/app/(dashboard)/financial/expenses/_components/expense-filters.tsx   # Not used in new list page
frontend/app/(dashboard)/financial/expenses/_components/expense-columns.tsx   # Not used in new list page
```

---

## Task 1: Backend — `get_expense_detail()` service method

**Files:**

- Modify: `core/services/financial_dashboard_service.py` (add method after `get_dashboard_summary`)

This method returns full expense details for a given type+id+month. For persons, it returns all expense installments and single expenses grouped by category (cards, loans, fixed, one-time, offsets, stipends) with full category/subcategory info. For utilities, returns building-grouped data. For fixed categories, returns the item list.

- [ ] **Step 1: Add `get_expense_detail()` to FinancialDashboardService**

```python
@staticmethod
def get_expense_detail(
    detail_type: str, detail_id: int | None, year: int, month: int
) -> dict[str, Any]:
    """Return full expense detail for a specific category/person."""
    month_start = date(year, month, 1)
    next_month = _next_month_start(year, month)

    if detail_type == "person":
        if detail_id is None:
            raise ValueError("detail_id is required for person type")
        person = Person.objects.get(pk=detail_id)
        data = FinancialDashboardService._get_person_month_expenses(
            person, month_start, next_month
        )
        # Use waterfall for payment allocation
        if data["is_payable"]:
            waterfall = FinancialDashboardService._get_person_waterfall(
                person, year, month
            )
            current_key = f"{year}-{month:02d}"
            current_alloc = waterfall.get(current_key)
            if current_alloc:
                data["total_paid"] = current_alloc["allocated_paid"]
                data["pending"] = current_alloc["pending"]
        return {"detail_type": "person", **data}

    if detail_type in ("electricity", "water"):
        expense_type = (
            ExpenseType.ELECTRICITY_BILL if detail_type == "electricity"
            else ExpenseType.WATER_BILL
        )
        utility_data = FinancialDashboardService._build_utility_by_building(
            expense_type, month_start, next_month
        )
        return {"detail_type": detail_type, "label": detail_type, **utility_data}

    if detail_type == "iptu":
        # Reuse IPTU logic from _build_expense_summary
        # (extract into helper if needed)
        ...
        return {"detail_type": "iptu", ...}

    if detail_type in ("internet", "celular", "sitio", "outros_fixed"):
        fixed = FinancialDashboardService._build_fixed_expense_categories(month_start)
        return {"detail_type": detail_type, **fixed[detail_type]}

    if detail_type == "employee":
        # Employee salary details
        ...
        return {"detail_type": "employee", ...}

    raise ValueError(f"Unknown detail type: {detail_type}")
```

The full implementation should include all category/subcategory data from the Expense model's `category` FK (with nested subcategories). Enrich each expense item with:

- `category_id`, `category_name`, `category_color`
- `subcategory_id`, `subcategory_name` (from `category.parent` relationship)
- `notes` field from Expense model
- `expense_id` for PATCH/DELETE mutations

- [ ] **Step 2: Run ruff check**

Run: `python -m ruff check core/services/financial_dashboard_service.py`
Expected: All checks passed!

- [ ] **Step 3: Commit**

```bash
git add core/services/financial_dashboard_service.py
git commit -m "feat(financial): add get_expense_detail service method"
```

---

## Task 2: Backend — `expense_detail` ViewSet action

**Files:**

- Modify: `core/viewsets/financial_dashboard_views.py` (add action to FinancialDashboardViewSet)

- [ ] **Step 1: Add expense_detail action**

Add after the `dashboard_summary` action (around line 90):

```python
@action(detail=False, methods=["get"], url_path="expense_detail")
def expense_detail(self, request: Request) -> Response:
    detail_type = request.query_params.get("type")
    if not detail_type:
        return Response(
            {"error": "O parâmetro 'type' é obrigatório."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    detail_id_str = request.query_params.get("id")
    detail_id = int(detail_id_str) if detail_id_str else None

    today = date.today()
    try:
        year = int(request.query_params.get("year", today.year))
        month = int(request.query_params.get("month", today.month))
    except ValueError:
        return Response(
            {"error": "Os parâmetros 'year' e 'month' devem ser inteiros válidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        data = FinancialDashboardService.get_expense_detail(
            detail_type, detail_id, year, month
        )
    except (Person.DoesNotExist, ValueError) as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(data, status=status.HTTP_200_OK)
```

- [ ] **Step 2: Run ruff check**

Run: `python -m ruff check core/viewsets/financial_dashboard_views.py`

- [ ] **Step 3: Test endpoint manually**

Run: `curl http://localhost:8008/api/financial-dashboard/expense_detail/?type=person&id=3&year=2026&month=3` (with auth header)
Expected: JSON with Alvaro's full expense detail

- [ ] **Step 4: Commit**

```bash
git add core/viewsets/financial_dashboard_views.py
git commit -m "feat(financial): add expense_detail API endpoint"
```

---

## Task 3: Frontend — `useExpenseDetail()` hook + types

**Files:**

- Modify: `frontend/lib/api/hooks/use-financial-dashboard.ts`

- [ ] **Step 1: Add ExpenseDetailItem interface and useExpenseDetail hook**

Add after the existing interfaces (around line 100):

```typescript
export interface ExpenseDetailItem {
  expense_id: number;
  description: string;
  card_name?: string | null;
  installment_number?: number | null;
  total_installments?: number | null;
  category_id?: number | null;
  category_name?: string | null;
  category_color?: string | null;
  subcategory_id?: number | null;
  subcategory_name?: string | null;
  notes?: string | null;
  amount: number;
  due_date?: string | null;
}

export interface ExpenseDetailResponse {
  detail_type: string;
  person_id?: number;
  person_name?: string;
  total?: number;
  total_paid?: number;
  pending?: number;
  is_payable?: boolean;
  card_total?: number;
  card_details?: ExpenseDetailItem[];
  loan_total?: number;
  loan_details?: ExpenseDetailItem[];
  fixed_total?: number;
  fixed_details?: ExpenseDetailItem[];
  one_time_total?: number;
  one_time_details?: ExpenseDetailItem[];
  offset_total?: number;
  offset_details?: ExpenseDetailItem[];
  stipend_total?: number;
  stipend_details?: ExpenseDetailItem[];
  // Utility types
  by_building?: UtilityBuildingEntry[];
  // Simple types (internet, celular, etc.)
  details?: ExpenseDetailItem[];
  label?: string;
}
```

Add hook:

```typescript
export function useExpenseDetail(
  type: string,
  id: number | null,
  year: number,
  month: number,
) {
  return useQuery({
    queryKey: ["financial-dashboard", "expense_detail", type, id, year, month],
    queryFn: async () => {
      const params: Record<string, string | number> = { type, year, month };
      if (id !== null) params.id = id;
      const { data } = await apiClient.get<ExpenseDetailResponse>(
        "/financial-dashboard/expense_detail/",
        { params },
      );
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
    enabled: Boolean(type),
  });
}
```

- [ ] **Step 2: Run type-check**

Run: `cd frontend && eval "$(fnm env --shell bash)" && npm run type-check`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api/hooks/use-financial-dashboard.ts
git commit -m "feat(financial): add useExpenseDetail hook and types"
```

---

## Task 4: Frontend — Month Navigator component

**Files:**

- Create: `frontend/app/(dashboard)/financial/expenses/_components/month-navigator.tsx`

- [ ] **Step 1: Create MonthNavigator component**

Simple component with ← arrow | "Março de 2026" | → arrow. Uses `formatMonthYear()` from `@/lib/utils/formatters`. Calls `onMonthChange(year, month)` callback.

```typescript
'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { formatMonthYear } from '@/lib/utils/formatters';

export function MonthNavigator({
  year,
  month,
  onMonthChange,
}: {
  year: number;
  month: number;
  onMonthChange: (year: number, month: number) => void;
}) {
  const goBack = () => {
    const newMonth = month === 1 ? 12 : month - 1;
    const newYear = month === 1 ? year - 1 : year;
    onMonthChange(newYear, newMonth);
  };

  const goForward = () => {
    const newMonth = month === 12 ? 1 : month + 1;
    const newYear = month === 12 ? year + 1 : year;
    onMonthChange(newYear, newMonth);
  };

  return (
    <div className="flex items-center gap-3">
      <Button variant="outline" size="icon" onClick={goBack}>
        <ChevronLeft className="h-4 w-4" />
      </Button>
      <span className="text-lg font-semibold min-w-[180px] text-center">
        {formatMonthYear(year, month)}
      </span>
      <Button variant="outline" size="icon" onClick={goForward}>
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/(dashboard)/financial/expenses/_components/month-navigator.tsx
git commit -m "feat(financial): add MonthNavigator component"
```

---

## Task 5: Frontend — Expense List Table component

**Files:**

- Create: `frontend/app/(dashboard)/financial/expenses/_components/expense-list-table.tsx`

- [ ] **Step 1: Create ExpenseListTable component**

Renders a table from `DashboardSummary.expense_summary` data. Each row shows: icon + name, type badge, value, progress bar (for payable persons), "Ver detalhes →" link.

The link navigates to `/financial/expenses/details?type=<type>&id=<id>&year=<year>&month=<month>`.

Use the same progress bar logic from the dashboard's `PersonExpenseItem` component. For non-payable persons, show subtitle "Salário administração condomínio".

Map each expense category to a row:

- `by_person` → one row per person with `type=person&id={person_id}`
- `water` → `type=water`
- `electricity` → `type=electricity`
- `iptu` → `type=iptu`
- `internet` → `type=internet`
- `celular` → `type=celular`
- `sitio` → `type=sitio`
- `outros_fixed` → `type=outros_fixed`
- `employee` → `type=employee`

Use lucide-react icons consistent with the dashboard expense cards.

- [ ] **Step 2: Run type-check**

Run: `cd frontend && eval "$(fnm env --shell bash)" && npm run type-check`

- [ ] **Step 3: Commit**

```bash
git add frontend/app/(dashboard)/financial/expenses/_components/expense-list-table.tsx
git commit -m "feat(financial): add ExpenseListTable component"
```

---

## Task 6: Frontend — Rewrite expenses list page

**Files:**

- Rewrite: `frontend/app/(dashboard)/financial/expenses/page.tsx`

- [ ] **Step 1: Rewrite page.tsx**

Replace the current CRUD table with the monthly summary list. Uses `useDashboardSummary(year, month)` for data, `MonthNavigator` for month selection, `ExpenseListTable` for the table.

State: `year` and `month` as `useState` (initialized from `new Date()`).

Layout:

```
<h1>Despesas</h1>
<p>Gerencie despesas mensal</p>
<Card>
  <CardHeader>
    <MonthNavigator /> ... Total: R$ X
  </CardHeader>
  <CardContent>
    <ExpenseListTable data={summary} year={year} month={month} />
  </CardContent>
</Card>
```

Handle loading/error states with skeleton and error message.

- [ ] **Step 2: Run type-check and lint**

Run: `cd frontend && eval "$(fnm env --shell bash)" && npm run type-check && npm run lint`

- [ ] **Step 3: Test in browser**

Navigate to `/financial/expenses`. Verify: month navigation works, all expense categories render, progress bars show for payable persons, "Ver detalhes" links have correct URLs.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/(dashboard)/financial/expenses/page.tsx
git commit -m "feat(financial): rewrite expenses page as monthly summary list"
```

---

## Task 7: Frontend — Detail page header component

**Files:**

- Create: `frontend/app/(dashboard)/financial/expenses/details/_components/detail-header.tsx`

- [ ] **Step 1: Create DetailHeader component**

Shows: back link (breadcrumb), name + icon, total value, progress bar + pago/pendente (if payable), "Registrar Pagamento" button linking to `/financial/person-payments?person_id={id}`.

Props: `title: string`, `total: number`, `totalPaid?: number`, `pending?: number`, `isPayable?: boolean`, `personId?: number`, `monthLabel: string`.

- [ ] **Step 2: Commit**

```bash
git add frontend/app/(dashboard)/financial/expenses/details/_components/detail-header.tsx
git commit -m "feat(financial): add expense detail header component"
```

---

## Task 8: Frontend — Detail table component

**Files:**

- Create: `frontend/app/(dashboard)/financial/expenses/details/_components/expense-detail-table.tsx`

- [ ] **Step 1: Create ExpenseDetailTable component**

Renders a table of `ExpenseDetailItem[]` with columns: Descrição, Cartão, Parcela Atual, Total Parcelas, Categoria (badge with color), Subcategoria, Notas, Valor, Ações (edit/delete icons).

Shows first 10 items. "Ver todos (N itens)" button to expand. Uses `useState` for expansion.

Edit button calls `onEdit(item)`. Delete button calls `onDelete(item)`.

- [ ] **Step 2: Commit**

```bash
git add frontend/app/(dashboard)/financial/expenses/details/_components/expense-detail-table.tsx
git commit -m "feat(financial): add expense detail table component"
```

---

## Task 9: Frontend — Expense accordion component

**Files:**

- Create: `frontend/app/(dashboard)/financial/expenses/details/_components/expense-accordion.tsx`

- [ ] **Step 1: Create ExpenseAccordion component**

Collapsible section with: title (colored), item count, total value in header. Body contains `ExpenseDetailTable`. Uses `useState` for open/close.

Props: `title: string`, `color: string`, `items: ExpenseDetailItem[]`, `total: number`, `onEdit`, `onDelete`.

- [ ] **Step 2: Commit**

```bash
git add frontend/app/(dashboard)/financial/expenses/details/_components/expense-accordion.tsx
git commit -m "feat(financial): add expense accordion component"
```

---

## Task 10: Frontend — Expense edit modal

**Files:**

- Create: `frontend/app/(dashboard)/financial/expenses/details/_components/expense-edit-modal.tsx`

- [ ] **Step 1: Create ExpenseEditModal component**

Modal (Shadcn Dialog) with fields:

- Description (text input)
- Value (currency input)
- Category (dropdown from `useExpenseCategories()`)
- Subcategory (dropdown filtered by selected category's subcategories, clears when category changes)
- Notes (textarea)

On save: confirmation dialog → PATCH `/api/expenses/{id}/` or `/api/expense-installments/{id}/` → invalidate queries → close modal.

Use React Hook Form + Zod for validation. Pre-populate from selected item data.

Ref: existing category hook at `frontend/lib/api/hooks/use-expense-categories.ts` and schema at `frontend/lib/schemas/expense-category.schema.ts`.

- [ ] **Step 2: Run type-check**

Run: `cd frontend && eval "$(fnm env --shell bash)" && npm run type-check`

- [ ] **Step 3: Commit**

```bash
git add frontend/app/(dashboard)/financial/expenses/details/_components/expense-edit-modal.tsx
git commit -m "feat(financial): add expense edit modal with cascading categories"
```

---

## Task 11: Frontend — Detail page assembly

**Files:**

- Create: `frontend/app/(dashboard)/financial/expenses/details/page.tsx`

- [ ] **Step 1: Create detail page**

Uses `useSearchParams()` to read `type`, `id`, `year`, `month`. Calls `useExpenseDetail(type, id, year, month)`.

Layout:

```
<DetailHeader ... />
<ExpenseAccordion title="Cartões" items={data.card_details} ... />
<ExpenseAccordion title="Empréstimos" items={data.loan_details} ... />
<ExpenseAccordion title="Gastos Fixos" items={data.fixed_details} ... />
<ExpenseAccordion title="Gastos Únicos" items={data.one_time_details} ... />
<ExpenseAccordion title="Descontos" items={data.offset_details} ... />
<ExpenseAccordion title="Estipêndios" items={data.stipend_details} ... />
<ExpenseEditModal ... />
<DeleteConfirmDialog ... />
```

For utility types (`electricity`, `water`, `iptu`): render one accordion per building from `data.by_building`.
For simple types (`internet`, `celular`, `sitio`, `outros_fixed`, `employee`): render a single flat table from `data.details`.

Handle loading with skeleton, error with message card.

- [ ] **Step 2: Run type-check and lint**

Run: `cd frontend && eval "$(fnm env --shell bash)" && npm run type-check && npm run lint`

- [ ] **Step 3: Test in browser**

Navigate to `/financial/expenses`, click "Ver detalhes" on Rodrigo. Verify:

- Header shows correct total and progress
- Accordions expand/collapse
- Table shows 10 items with "Ver todos" button
- Edit modal opens and saves correctly
- Delete confirmation works

- [ ] **Step 4: Commit**

```bash
git add frontend/app/(dashboard)/financial/expenses/details/
git commit -m "feat(financial): add expense detail page with accordions and edit modal"
```

---

## Task 12: Dashboard — Add "Ver detalhes" links to modals

**Files:**

- Modify: `frontend/app/(dashboard)/financial/_components/expense-summary-card.tsx`

- [ ] **Step 1: Add "Ver detalhes" link to PersonDetailModal**

In the `PersonDetailModal` component (after the payment info section, around line 275), add:

```tsx
<a
  href={`/financial/expenses/details?type=person&id=${person.person_id}&year=${year}&month=${month}`}
  className="block text-center text-sm text-blue-600 hover:underline pt-2 border-t"
>
  Ver detalhes completos
</a>
```

Pass `year` and `month` as props from the parent component.

- [ ] **Step 2: Add "Ver detalhes" link to UtilityDetailModal**

Similar link at the bottom of the utility modal, with appropriate type param.

- [ ] **Step 3: Add "Ver detalhes" link to SimpleDetailModal**

Similar link for internet, celular, sitio, outros_fixed, employee modals.

- [ ] **Step 4: Run type-check and lint**

Run: `cd frontend && eval "$(fnm env --shell bash)" && npm run type-check && npm run lint`

- [ ] **Step 5: Test in browser**

Open dashboard, click on Rodrigo card → modal → click "Ver detalhes completos" → navigates to detail page.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/(dashboard)/financial/_components/expense-summary-card.tsx
git commit -m "feat(financial): add 'Ver detalhes' links to dashboard expense modals"
```

---

## Task 13: Cache invalidation + final integration

**Files:**

- Modify: `frontend/app/(dashboard)/financial/expenses/details/_components/expense-edit-modal.tsx`
- Modify: `frontend/app/(dashboard)/financial/expenses/details/page.tsx`

- [ ] **Step 1: Ensure mutations invalidate all related queries**

On successful edit/delete, invalidate:

```typescript
void queryClient.invalidateQueries({ queryKey: ["financial-dashboard"] });
void queryClient.invalidateQueries({ queryKey: ["expenses"] });
void queryClient.invalidateQueries({ queryKey: ["expense-installments"] });
```

This ensures: dashboard summary, expense detail, and any cached expense lists all refresh.

- [ ] **Step 2: Full integration test**

1. Open dashboard → verify expense cards match
2. Click "Ver detalhes" on Rodrigo → detail page loads
3. Expand Cartões accordion → see 74 items with correct columns
4. Click edit on an item → modal opens → change category → save → confirm
5. Verify item updated in table
6. Click delete on an item → confirm → item removed
7. Go back to dashboard → verify totals updated
8. Navigate to `/financial/expenses` → verify list matches dashboard
9. Change month → verify data updates

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat(financial): complete expenses page redesign with detail drill-down"
```
