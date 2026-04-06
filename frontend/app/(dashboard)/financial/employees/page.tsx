'use client';

import { useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Plus, Loader2, Pencil, Trash2, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { DataTable, type Column } from '@/components/tables/data-table';
import { DeleteConfirmDialog } from '@/components/shared/delete-confirm-dialog';
import { cn } from '@/lib/utils';
import {
  useEmployeePayments,
  useDeleteEmployeePayment,
  useMarkEmployeePaymentPaid,
} from '@/lib/api/hooks/use-employee-payments';
import { type EmployeePayment } from '@/lib/schemas/employee-payment.schema';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import { useAuthStore } from '@/store/auth-store';
import { formatCurrency } from '@/lib/utils/formatters';

function ModalLoader() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-background/80">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

const EmployeePaymentFormModal = dynamic(
  () =>
    import('./_components/employee-payment-form-modal').then(
      (mod) => mod.EmployeePaymentFormModal,
    ),
  { loading: () => <ModalLoader />, ssr: false },
);

function formatReferenceMonth(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  return date
    .toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' })
    .replace('.', '')
    .replace(/^(\w)/, (c) => c.toUpperCase());
}

interface EmployeePaymentActionHandlers {
  onEdit: (payment: EmployeePayment) => void;
  onDelete: (payment: EmployeePayment) => void;
  onMarkPaid: (payment: EmployeePayment) => void | Promise<void>;
  isDeleting: boolean;
  isMarkingPaid: boolean;
  isAdmin: boolean;
}

function createEmployeePaymentColumns(
  handlers: EmployeePaymentActionHandlers,
): Column<EmployeePayment>[] {
  return [
    {
      title: 'Mês Ref.',
      dataIndex: 'reference_month',
      key: 'reference_month',
      width: 110,
      render: (value) => formatReferenceMonth(value as string),
      sorter: (a, b) => a.reference_month.localeCompare(b.reference_month),
    },
    {
      title: 'Funcionário',
      key: 'person',
      width: 160,
      render: (_, record) => record.person?.name ?? '-',
    },
    {
      title: 'Salário Base',
      dataIndex: 'base_salary',
      key: 'base_salary',
      width: 130,
      render: (value) => formatCurrency(value as number),
      sorter: (a, b) => a.base_salary - b.base_salary,
    },
    {
      title: 'Variável',
      dataIndex: 'variable_amount',
      key: 'variable_amount',
      width: 120,
      render: (value) => formatCurrency(value as number),
    },
    {
      title: 'Compensação Aluguel',
      dataIndex: 'rent_offset',
      key: 'rent_offset',
      width: 160,
      render: (value) => (
        <span className="text-muted-foreground">{formatCurrency(value as number)}</span>
      ),
    },
    {
      title: 'Total Pago',
      key: 'total_paid',
      width: 130,
      render: (_, record) => (
        <span className="font-bold">
          {formatCurrency(record.base_salary + record.variable_amount)}
        </span>
      ),
      sorter: (a, b) =>
        a.base_salary + a.variable_amount - (b.base_salary + b.variable_amount),
    },
    {
      title: 'Faxinas',
      dataIndex: 'cleaning_count',
      key: 'cleaning_count',
      width: 90,
      align: 'center',
    },
    {
      title: 'Status',
      key: 'status',
      width: 110,
      align: 'center',
      render: (_, record) => (
        <Badge
          className={cn(
            record.is_paid
              ? 'bg-success/10 text-success'
              : 'bg-warning/10 text-warning',
          )}
        >
          {record.is_paid ? 'Pago' : 'Pendente'}
        </Badge>
      ),
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <TooltipProvider>
          <div className="flex items-center gap-1">
            {handlers.isAdmin && (
              <>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" aria-label="Editar" onClick={() => handlers.onEdit(record)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Editar</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Excluir"
                      onClick={() => handlers.onDelete(record)}
                      disabled={handlers.isDeleting}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Excluir</TooltipContent>
                </Tooltip>
              </>
            )}

            {handlers.isAdmin && !record.is_paid && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Marcar como Pago"
                    onClick={() => void handlers.onMarkPaid(record)}
                    disabled={handlers.isMarkingPaid}
                  >
                    <CheckCircle className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Marcar como Pago</TooltipContent>
              </Tooltip>
            )}
          </div>
        </TooltipProvider>
      ),
    },
  ];
}

export default function EmployeesPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;
  const { data: payments, isLoading, error } = useEmployeePayments();
  const deleteMutation = useDeleteEmployeePayment();
  const markPaidMutation = useMarkEmployeePaymentPaid();

  const crud = useCrudPage<EmployeePayment>({
    entityName: 'pagamento',
    entityNamePlural: 'pagamentos',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir pagamento.',
  });

  const handleDelete = useCallback(
    (payment: EmployeePayment) => {
      crud.setItemToDelete(payment);
      if (payment.id !== undefined) crud.handleDeleteClick(payment.id);
    },
    [crud],
  );

  const handleMarkPaid = useCallback(
    async (payment: EmployeePayment) => {
      if (payment.id === undefined) return;
      try {
        await markPaidMutation.mutateAsync(payment.id);
        toast.success('Pagamento marcado como pago');
      } catch {
        toast.error('Erro ao marcar pagamento como pago');
      }
    },
    [markPaidMutation],
  );

  const columns = useMemo(
    () =>
      createEmployeePaymentColumns({
        onEdit: crud.openEditModal,
        onDelete: handleDelete,
        onMarkPaid: handleMarkPaid,
        isDeleting: crud.isDeleting,
        isMarkingPaid: markPaidMutation.isPending,
        isAdmin,
      }),
    [
      crud.openEditModal,
      crud.isDeleting,
      handleDelete,
      handleMarkPaid,
      markPaidMutation.isPending,
      isAdmin,
    ],
  );

  if (error) {
    toast.error('Erro ao carregar pagamentos de funcionários');
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Funcionários</h1>
          <p className="text-muted-foreground mt-1">Gerencie pagamentos de funcionários</p>
        </div>
        {isAdmin && (
          <Button onClick={crud.openCreateModal}>
            <Plus className="h-4 w-4 mr-2" />
            Novo Pagamento
          </Button>
        )}
      </div>

      {/* Data Table */}
      <DataTable<EmployeePayment>
        columns={columns}
        dataSource={payments}
        loading={isLoading}
        rowKey="id"
      />

      {/* Form Modal */}
      <EmployeePaymentFormModal
        open={crud.isModalOpen}
        payment={crud.editingItem}
        onClose={crud.closeModal}
      />

      {/* Delete Dialog */}
      <DeleteConfirmDialog
        open={crud.deleteDialogOpen}
        onOpenChange={crud.setDeleteDialogOpen}
        itemName={
          crud.itemToDelete
            ? `pagamento de ${crud.itemToDelete.person?.name ?? 'funcionário'} em ${formatReferenceMonth(crud.itemToDelete.reference_month)}`
            : undefined
        }
        onConfirm={crud.handleDelete}
        isLoading={crud.isDeleting}
      />
    </div>
  );
}
