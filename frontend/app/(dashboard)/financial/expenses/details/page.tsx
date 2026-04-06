'use client';

import { useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { DeleteConfirmDialog } from '@/components/shared/delete-confirm-dialog';
import { toast } from 'sonner';
import {
  useExpenseDetail,
} from '@/lib/api/hooks/use-financial-dashboard';
import type { ExpenseDetailItem } from '@/lib/api/hooks/use-financial-dashboard';
import { queryKeys } from '@/lib/api/query-keys';
import { useMarkInstallmentPaid } from '@/lib/api/hooks/use-expense-installments';
import { useMarkExpensePaid } from '@/lib/api/hooks/use-expenses';
import { formatMonthYear, getDefaultExpenseDate, MONTH_ABBR } from '@/lib/utils/formatters';
import { apiClient } from '@/lib/api/client';
import { DetailHeader } from './_components/detail-header';
import { ExpenseAccordion } from './_components/expense-accordion';
import { ExpenseEditModal } from './_components/expense-edit-modal';
import { EmployeePaymentModal } from './_components/employee-payment-modal';
import { OverdueSection } from './_components/overdue-section';

const LABELS: Record<string, string> = {
  person: '',
  electricity: 'Contas de Luz',
  water: 'Contas de Água',
  iptu: 'IPTU',
  internet: 'Internet',
  celular: 'Celular / Claro',
  sitio: 'Sítio',
  outros_fixed: 'Outros Gastos Fixos',
  employee: 'Funcionários',
};

const UTILITY_TYPES = ['electricity', 'water', 'iptu'];

function DetailPageSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-24 w-full" />
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    </div>
  );
}

function ExpenseDetailContent() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  const type = searchParams.get('type') ?? '';
  const idParam = searchParams.get('id');
  const id = idParam !== null ? Number(idParam) : null;
  const now = new Date();
  const year = Number(searchParams.get('year') ?? now.getFullYear());
  const month = Number(searchParams.get('month') ?? now.getMonth() + 1);

  const [editTarget, setEditTarget] = useState<ExpenseDetailItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ExpenseDetailItem | null>(null);
  const [employeeEditTarget, setEmployeeEditTarget] = useState<Record<string, unknown> | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isCreatingNextMonth, setIsCreatingNextMonth] = useState(false);

  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  const currentMonthAbbr = MONTH_ABBR[month - 1] ?? '';
  const nextMonthAbbr = MONTH_ABBR[nextMonth - 1] ?? '';

  const { data, isLoading, error } = useExpenseDetail(type, id, year, month);
  const markInstallmentPaid = useMarkInstallmentPaid();
  const markExpensePaid = useMarkExpensePaid();

  const isNonPersonType = type !== 'person' && type !== 'employee';

  const monthLabel = formatMonthYear(year, month);

  const handleMarkPaid = async (item: ExpenseDetailItem) => {
    try {
      if (item.installment_id) {
        await markInstallmentPaid.mutateAsync(item.installment_id);
      } else {
        await markExpensePaid.mutateAsync(item.expense_id);
      }
      toast.success(`"${item.description}" marcada como paga`);
    } catch {
      toast.error('Erro ao marcar como paga');
    }
  };

  const handleSaved = async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.financialDashboard.all });
    await queryClient.invalidateQueries({ queryKey: queryKeys.expenses.all });
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiClient.delete(`/expenses/${deleteTarget.expense_id}/`);
      toast.success('Despesa excluída com sucesso');
    } catch {
      toast.error('Erro ao excluir despesa');
    } finally {
      setDeleteTarget(null);
      await queryClient.invalidateQueries({ queryKey: queryKeys.financialDashboard.all });
      await queryClient.invalidateQueries({ queryKey: queryKeys.expenses.all });
    }
  };

  if (!type) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        Tipo de despesa não especificado.
      </div>
    );
  }

  if (isLoading) {
    return <DetailPageSkeleton />;
  }

  if (error ?? !data) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        Erro ao carregar detalhes da despesa.
      </div>
    );
  }

  const title =
    type === 'person'
      ? (data.person_name ?? 'Pessoa')
      : (LABELS[type] ?? type);

  const total = data.total ?? 0;

  return (
    <div className="space-y-6">
      <DetailHeader
        title={title}
        total={total}
        totalPaid={data.total_paid}
        pending={data.pending}
        isPayable={data.is_payable}
        personId={data.person_id}
        monthLabel={monthLabel}
        year={year}
        month={month}
      />

      <div className="flex justify-end gap-2">
        <Button onClick={() => setIsCreating(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Nova Despesa ({currentMonthAbbr})
        </Button>
        <Button variant="outline" onClick={() => setIsCreatingNextMonth(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Nova Despesa ({nextMonthAbbr})
        </Button>
      </div>

      {(data.overdue?.length ?? 0) > 0 && (
        <OverdueSection
          items={data.overdue ?? []}
          total={data.overdue_total ?? 0}
          onEdit={setEditTarget}
          onDelete={setDeleteTarget}
          onPaid={handleSaved}
        />
      )}

      <Card>
        <CardContent className="pt-6 space-y-3">
          {type === 'person' && (
            <>
              {(data.card_details?.length ?? 0) > 0 && (data.card_total ?? 0) > 0 && (
                <ExpenseAccordion
                  title="Cartões"
                  color="text-warning"
                  items={data.card_details ?? []}
                  total={data.card_total ?? 0}
                  onEdit={setEditTarget}
                  onDelete={setDeleteTarget}
                  groupBy="card_name"
                />
              )}
              {(data.loan_details?.length ?? 0) > 0 && (data.loan_total ?? 0) > 0 && (
                <ExpenseAccordion
                  title="Empréstimos"
                  color="text-destructive"
                  items={data.loan_details ?? []}
                  total={data.loan_total ?? 0}
                  onEdit={setEditTarget}
                  onDelete={setDeleteTarget}
                />
              )}
              {(data.fixed_details?.length ?? 0) > 0 && (data.fixed_total ?? 0) > 0 && (
                <ExpenseAccordion
                  title="Despesas Fixas"
                  color="text-muted-foreground"
                  items={data.fixed_details ?? []}
                  total={data.fixed_total ?? 0}
                  onEdit={setEditTarget}
                  onDelete={setDeleteTarget}
                />
              )}
              {(data.one_time_details?.length ?? 0) > 0 && (data.one_time_total ?? 0) > 0 && (
                <ExpenseAccordion
                  title="Gastos Únicos"
                  color="text-info"
                  items={data.one_time_details ?? []}
                  total={data.one_time_total ?? 0}
                  onEdit={setEditTarget}
                  onDelete={setDeleteTarget}
                />
              )}
              {(data.offset_details?.length ?? 0) > 0 && (data.offset_total ?? 0) > 0 && (
                <ExpenseAccordion
                  title="Descontos"
                  color="text-success"
                  items={data.offset_details ?? []}
                  total={data.offset_total ?? 0}
                  onEdit={setEditTarget}
                  onDelete={setDeleteTarget}
                />
              )}
              {(data.stipend_details?.length ?? 0) > 0 && (data.stipend_total ?? 0) > 0 && (
                <ExpenseAccordion
                  title="Estipêndios"
                  color="text-primary"
                  items={data.stipend_details ?? []}
                  total={data.stipend_total ?? 0}
                  onEdit={setEditTarget}
                  onDelete={setDeleteTarget}
                />
              )}
            </>
          )}

          {UTILITY_TYPES.includes(type) &&
            (data.by_building ?? []).map((building) => {
              // Map bill/debt items, preserving expense_id/installment_id when available from API
              const mapToDetail = (item: Record<string, unknown>, idx: number): ExpenseDetailItem => ({
                expense_id: (item.expense_id as number) ?? 0,
                installment_id: (item.installment_id as number) ?? null,
                description: typeof item.description === 'string' ? item.description : '',
                amount: Number(item.amount ?? 0),
                card_name: null,
                installment_number: (item.installment_number as number) ?? null,
                total_installments: (item.total_installments as number) ?? null,
                category_id: (item.category_id as number) ?? null,
                category_name: (item.category_name as string) ?? null,
                category_color: (item.category_color as string) ?? null,
                subcategory_id: null,
                subcategory_name: null,
                notes: typeof item.notes === 'string' ? item.notes : (item.installment !== null && item.installment !== undefined ? `${item.installment as number}` : String(idx)),
              });

              const debts = building.debt_installments ?? [];
              const bills = building.bills ?? [];

              // When a building has both bills and debt installments,
              // the debt is already included in the bill value — show it as a note
              const debtNote = debts.length > 0 && bills.length > 0
                ? debts.map((d) => {
                    const rec = d as unknown as Record<string, unknown>;
                    const desc = typeof rec.description === 'string' ? rec.description : '';
                    const inst = rec.installment as string | undefined;
                    const amt = Number(rec.amount ?? 0);
                    return `${desc} ${inst ?? ''} (R$${amt.toFixed(2).replace('.', ',')})`;
                  }).join('; ')
                : null;

              const billItems = bills.map((bill, i) => {
                const item = mapToDetail(bill as unknown as Record<string, unknown>, i);
                if (debtNote) {
                  return { ...item, notes: `Inclui: ${debtNote}` };
                }
                return item;
              });

              // Only show debt items as standalone rows when there are no bills
              const debtItems = bills.length === 0
                ? debts.map((item, i) => mapToDetail(item as unknown as Record<string, unknown>, i))
                : [];

              const allItems = [...billItems, ...debtItems];
              const hasEditableItems = allItems.some((item) => item.expense_id > 0);

              return (
                <ExpenseAccordion
                  key={building.building_name}
                  title={`Prédio ${building.building_name}`}
                  color="text-warning"
                  items={allItems}
                  total={building.total}
                  onEdit={hasEditableItems ? setEditTarget : () => undefined}
                  onDelete={hasEditableItems ? setDeleteTarget : () => undefined}
                  onMarkPaid={hasEditableItems ? handleMarkPaid : undefined}
                  isMarkingPaid={markInstallmentPaid.isPending || markExpensePaid.isPending}
                />
              );
            })}

          {!UTILITY_TYPES.includes(type) && type !== 'person' && type !== 'employee' && (
            <ExpenseAccordion
              title={LABELS[type] ?? type}
              color="text-muted-foreground"
              items={data.details ?? []}
              total={data.total ?? 0}
              onEdit={setEditTarget}
              onDelete={setDeleteTarget}
              onMarkPaid={isNonPersonType ? handleMarkPaid : undefined}
              isMarkingPaid={markInstallmentPaid.isPending || markExpensePaid.isPending}
              defaultOpen
            />
          )}

          {type === 'employee' && (
            <ExpenseAccordion
              title={LABELS[type] ?? type}
              color="text-muted-foreground"
              items={data.details ?? []}
              total={data.total ?? 0}
              onEdit={(item) => {
                // Find the raw detail data with employee_payment_id
                const raw = (data.details ?? []).find(
                  (d) => d.description === item.description
                ) as unknown as Record<string, unknown> | undefined;
                if (raw?.employee_payment_id) {
                  setEmployeeEditTarget(raw);
                }
              }}
              onDelete={() => undefined}
              defaultOpen
            />
          )}
        </CardContent>
      </Card>

      {editTarget !== null && (
        <ExpenseEditModal
          mode="edit"
          item={editTarget}
          personId={id}
          detailType={type}
          onClose={() => setEditTarget(null)}
          onSaved={handleSaved}
        />
      )}

      {isCreating && (
        <ExpenseEditModal
          mode="create"
          personId={id}
          detailType={type}
          defaultExpenseDate={getDefaultExpenseDate(year, month)}
          onClose={() => setIsCreating(false)}
          onSaved={handleSaved}
        />
      )}

      {isCreatingNextMonth && (
        <ExpenseEditModal
          mode="create"
          personId={id}
          detailType={type}
          defaultExpenseDate={getDefaultExpenseDate(nextYear, nextMonth)}
          onClose={() => setIsCreatingNextMonth(false)}
          onSaved={handleSaved}
        />
      )}

      {employeeEditTarget !== null && (
        <EmployeePaymentModal
          payment={{
            employee_payment_id: employeeEditTarget.employee_payment_id as number,
            person_name: employeeEditTarget.person_name as string,
            base_salary: Number(employeeEditTarget.base_salary ?? 0),
            variable_amount: Number(employeeEditTarget.variable_amount ?? 0),
            notes: (employeeEditTarget.notes as string) ?? '',
          }}
          onClose={() => setEmployeeEditTarget(null)}
          onSaved={handleSaved}
        />
      )}

      <DeleteConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        itemName={deleteTarget?.description}
        onConfirm={handleDelete}
      />
    </div>
  );
}

export default function ExpenseDetailPage() {
  return (
    <Suspense fallback={<DetailPageSkeleton />}>
      <ExpenseDetailContent />
    </Suspense>
  );
}
