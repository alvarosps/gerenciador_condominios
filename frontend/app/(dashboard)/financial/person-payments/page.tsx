'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Plus, Pencil, Trash2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { DataTable } from '@/components/tables/data-table';
import type { Column } from '@/components/tables/data-table';
import { DeleteConfirmDialog } from '@/components/shared/delete-confirm-dialog';
import {
  usePersonPayments,
  useDeletePersonPayment,
} from '@/lib/api/hooks/use-person-payments';
import { usePersons } from '@/lib/api/hooks/use-persons';
import type { PersonPayment } from '@/lib/schemas/person-payment.schema';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import { useAuthStore } from '@/store/auth-store';
import { PersonMonthSummary } from '../_components/person-month-summary';

function ModalLoader() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-background/80">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

const PersonPaymentFormModal = dynamic(
  () =>
    import('./_components/person-payment-form-modal').then(
      (mod) => mod.PersonPaymentFormModal,
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

function getCurrentMonth(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  return `${year}-${month}`;
}

export default function PersonPaymentsPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const [selectedMonth, setSelectedMonth] = useState(getCurrentMonth());
  const [filterPersonId, setFilterPersonId] = useState<number | undefined>(undefined);
  const [paymentPersonId, setPaymentPersonId] = useState<number | undefined>(undefined);

  const selectedYear = Number(selectedMonth.split('-')[0]);
  const selectedMonthNum = Number(selectedMonth.split('-')[1]);

  const { data: persons } = usePersons();
  const { data: allPayments, isLoading, error } = usePersonPayments({
    reference_month: selectedMonth + '-01',
    person_id: filterPersonId,
  });
  const deleteMutation = useDeletePersonPayment();

  const crud = useCrudPage<PersonPayment>({
    entityName: 'pagamento',
    entityNamePlural: 'pagamentos',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir pagamento.',
  });

  const relevantPersons = useMemo(
    () => persons?.filter((p) => !p.is_employee) ?? [],
    [persons],
  );

  const filteredPayments = useMemo(() => {
    if (!allPayments) return [];
    return allPayments;
  }, [allPayments]);

  const handleRegisterPaymentForPerson = useCallback(
    (personId: number) => {
      setPaymentPersonId(personId);
      crud.openCreateModal();
    },
    [crud],
  );

  const handleDelete = useCallback(
    (payment: PersonPayment) => {
      crud.setItemToDelete(payment);
      if (payment.id !== undefined) crud.handleDeleteClick(payment.id);
    },
    [crud],
  );

  const columns: Column<PersonPayment>[] = useMemo(
    () => [
      {
        title: 'Pessoa',
        key: 'person',
        render: (_, record) => record.person?.name ?? '-',
        sorter: (a: PersonPayment, b: PersonPayment) =>
          (a.person?.name ?? '').localeCompare(b.person?.name ?? ''),
      },
      {
        title: 'Mês Ref.',
        key: 'reference_month',
        render: (_, record) => formatReferenceMonth(record.reference_month),
        sorter: (a: PersonPayment, b: PersonPayment) =>
          a.reference_month.localeCompare(b.reference_month),
      },
      {
        title: 'Valor',
        key: 'amount',
        render: (_, record) => formatCurrency(record.amount),
        sorter: (a: PersonPayment, b: PersonPayment) => a.amount - b.amount,
      },
      {
        title: 'Data Pgto.',
        key: 'payment_date',
        render: (_, record) => formatDate(record.payment_date),
        sorter: (a: PersonPayment, b: PersonPayment) =>
          a.payment_date.localeCompare(b.payment_date),
      },
      {
        title: 'Notas',
        key: 'notes',
        render: (_, record) => record.notes ?? '-',
      },
      ...(isAdmin
        ? [
            {
              title: 'Ações',
              key: 'actions',
              width: 120,
              fixed: 'right' as const,
              render: (_: unknown, record: PersonPayment) => (
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => crud.openEditModal(record)}
                  >
                    <Pencil className="h-4 w-4 mr-1" />
                    Editar
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(record)}
                    disabled={crud.isDeleting}
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Excluir
                  </Button>
                </div>
              ),
            },
          ]
        : []),
    ],
    [crud, handleDelete, isAdmin],
  );

  useEffect(() => {
    if (error) toast.error('Erro ao carregar pagamentos');
  }, [error]);

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Pagamentos a Pessoas</h1>
          <p className="text-gray-600 mt-1">
            Controle de pagamentos mensais às pessoas
          </p>
        </div>
        {isAdmin && (
          <Button onClick={() => { setPaymentPersonId(undefined); crud.openCreateModal(); }}>
            <Plus className="h-4 w-4 mr-2" />
            Registrar Pagamento
          </Button>
        )}
      </div>

      {/* Filters */}
      <Card className="mb-4 p-4">
        <div className="flex gap-4 flex-wrap items-end">
          <div className="flex-1 min-w-[180px]">
            <label className="block text-sm font-medium mb-2">Pessoa</label>
            <Select
              value={filterPersonId !== undefined ? String(filterPersonId) : 'all'}
              onValueChange={(value) =>
                setFilterPersonId(value === 'all' ? undefined : Number(value))
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Todas as pessoas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas as pessoas</SelectItem>
                {relevantPersons.map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 min-w-[160px]">
            <label className="block text-sm font-medium mb-2">Mês</label>
            <Input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
            />
          </div>
        </div>
      </Card>

      {/* Person summary cards */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Resumo do Mês</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {relevantPersons.map((person) => (
            <PersonMonthSummary
              key={person.id}
              personId={person.id ?? 0}
              personName={person.name}
              personRelationship={person.relationship}
              year={selectedYear}
              month={selectedMonthNum}
              showPaymentButton={isAdmin}
              onRegisterPayment={() => handleRegisterPaymentForPerson(person.id ?? 0)}
            />
          ))}
          {relevantPersons.length === 0 && (
            <Card className="col-span-full p-6 text-center text-muted-foreground">
              Nenhuma pessoa cadastrada
            </Card>
          )}
        </div>
      </div>

      {/* Payment history table */}
      <h2 className="text-lg font-semibold mb-3">Histórico de Pagamentos</h2>
      <DataTable<PersonPayment>
        columns={columns}
        dataSource={filteredPayments}
        loading={isLoading}
        rowKey="id"
      />

      <PersonPaymentFormModal
        open={crud.isModalOpen}
        personPayment={crud.editingItem}
        onClose={crud.closeModal}
        defaultPersonId={paymentPersonId}
        defaultReferenceMonth={selectedMonth}
      />

      <DeleteConfirmDialog
        open={crud.deleteDialogOpen}
        onOpenChange={crud.setDeleteDialogOpen}
        itemName={
          crud.itemToDelete
            ? `${crud.itemToDelete.person?.name ?? 'Pagamento'} - ${formatReferenceMonth(crud.itemToDelete.reference_month)}`
            : undefined
        }
        onConfirm={crud.handleDelete}
        isLoading={crud.isDeleting}
      />
    </div>
  );
}
