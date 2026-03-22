'use client';

import { useState, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { Plus, Loader2, Download } from 'lucide-react';
import { toast } from 'sonner';
import { DataTable } from '@/components/tables/data-table';
import { DeleteConfirmDialog } from '@/components/shared/delete-confirm-dialog';
import { ExpenseFiltersCard, type ExtendedExpenseFilters } from './_components/expense-filters';
import { createExpenseColumns } from './_components/expense-columns';
import { InstallmentsDrawer } from './_components/installments-drawer';
import {
  useExpenses,
  useDeleteExpense,
  useMarkExpensePaid,
} from '@/lib/api/hooks/use-expenses';
import { type Expense } from '@/lib/schemas/expense.schema';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import { useExport, expenseExportColumns } from '@/lib/hooks/use-export';
import { useAuthStore } from '@/store/auth-store';

function ModalLoader() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-background/80">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

const ExpenseFormModal = dynamic(
  () => import('./_components/expense-form-modal').then((mod) => mod.ExpenseFormModal),
  { loading: () => <ModalLoader />, ssr: false },
);

export default function ExpensesPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;
  const [filters, setFilters] = useState<ExtendedExpenseFilters>({});
  const [selectedExpenseForInstallments, setSelectedExpenseForInstallments] = useState<Expense | null>(null);

  const { data: expenses, isLoading, error } = useExpenses(filters);
  const deleteMutation = useDeleteExpense();
  const markPaidMutation = useMarkExpensePaid();
  const { exportToExcel, isExporting } = useExport();

  const crud = useCrudPage<Expense>({
    entityName: 'despesa',
    entityNamePlural: 'despesas',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir despesa. Verifique se n\u00e3o h\u00e1 parcelas vinculadas.',
  });

  const handleDelete = useCallback(
    (expense: Expense) => {
      crud.setItemToDelete(expense);
      if (expense.id !== undefined) crud.handleDeleteClick(expense.id);
    },
    [crud],
  );

  const handleViewInstallments = useCallback((expense: Expense) => {
    setSelectedExpenseForInstallments(expense);
  }, []);

  const markPaid = useCallback(
    async (expenseId: number) => {
      try {
        await markPaidMutation.mutateAsync(expenseId);
        toast.success('Despesa marcada como paga');
      } catch {
        toast.error('Erro ao marcar despesa como paga');
      }
    },
    [markPaidMutation],
  );

  const handleMarkPaid = useCallback(
    (expense: Expense) => {
      if (expense.id !== undefined) void markPaid(expense.id);
    },
    [markPaid],
  );

  const columns = useMemo(
    () =>
      createExpenseColumns({
        onEdit: crud.openEditModal,
        onDelete: handleDelete,
        onViewInstallments: handleViewInstallments,
        onMarkPaid: handleMarkPaid,
        isDeleting: crud.isDeleting,
        isMarkingPaid: markPaidMutation.isPending,
        isAdmin,
      }),
    [crud.openEditModal, crud.isDeleting, handleDelete, handleViewInstallments, handleMarkPaid, markPaidMutation.isPending, isAdmin],
  );

  if (error) {
    toast.error('Erro ao carregar despesas');
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Despesas</h1>
          <p className="text-gray-600 mt-1">
            Gerencie despesas, parcelas e gastos fixos
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => expenses && exportToExcel(expenses as Record<string, unknown>[], expenseExportColumns, { filename: 'despesas' })}
            disabled={isExporting || !expenses?.length}
          >
            <Download className="h-4 w-4 mr-2" />
            Exportar
          </Button>
          {isAdmin && (
            <Button onClick={crud.openCreateModal}>
              <Plus className="h-4 w-4 mr-2" />
              Nova Despesa
            </Button>
          )}
        </div>
      </div>

      {/* Filters */}
      <ExpenseFiltersCard filters={filters} onFiltersChange={setFilters} />

      {/* Data Table */}
      <DataTable<Expense>
        columns={columns}
        dataSource={expenses}
        loading={isLoading}
        rowKey="id"
      />

      {/* Form Modal */}
      <ExpenseFormModal
        open={crud.isModalOpen}
        expense={crud.editingItem}
        onClose={crud.closeModal}
      />

      {/* Installments Drawer */}
      <InstallmentsDrawer
        open={selectedExpenseForInstallments !== null}
        expense={selectedExpenseForInstallments}
        onClose={() => setSelectedExpenseForInstallments(null)}
      />

      {/* Delete Dialog */}
      <DeleteConfirmDialog
        open={crud.deleteDialogOpen}
        onOpenChange={crud.setDeleteDialogOpen}
        itemName={crud.itemToDelete?.description}
        onConfirm={crud.handleDelete}
        isLoading={crud.isDeleting}
      />
    </div>
  );
}
