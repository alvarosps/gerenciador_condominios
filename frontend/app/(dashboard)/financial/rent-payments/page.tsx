'use client';

import { useState, useMemo, useCallback } from 'react';
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
import { Plus, Pencil, Trash2, Loader2, Download } from 'lucide-react';
import { toast } from 'sonner';
import { DataTable } from '@/components/tables/data-table';
import type { Column } from '@/components/tables/data-table';
import { DeleteConfirmDialog } from '@/components/shared/delete-confirm-dialog';
import {
  useRentPayments,
  useDeleteRentPayment,
} from '@/lib/api/hooks/use-rent-payments';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useApartments } from '@/lib/api/hooks/use-apartments';
import type { RentPayment } from '@/lib/schemas/rent-payment.schema';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import { useExport, rentPaymentExportColumns } from '@/lib/hooks/use-export';
import { useAuthStore } from '@/store/auth-store';

function ModalLoader() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-background/80">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

const RentPaymentFormModal = dynamic(
  () =>
    import('./_components/rent-payment-form-modal').then(
      (mod) => mod.RentPaymentFormModal,
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

export default function RentPaymentsPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;
  const [buildingId, setBuildingId] = useState<number | undefined>(undefined);
  const [apartmentId, setApartmentId] = useState<number | undefined>(undefined);
  const [monthFrom, setMonthFrom] = useState('');
  const [monthTo, setMonthTo] = useState('');

  const { exportToExcel, isExporting } = useExport();
  const { data: allPayments, isLoading, error } = useRentPayments();
  const { data: buildings } = useBuildings();
  const { data: apartments } = useApartments(
    buildingId ? { building_id: buildingId } : undefined,
  );
  const deleteMutation = useDeleteRentPayment();

  const crud = useCrudPage<RentPayment>({
    entityName: 'pagamento',
    entityNamePlural: 'pagamentos',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir pagamento.',
  });

  const filteredPayments = useMemo(() => {
    if (!allPayments) return [];

    return allPayments.filter((payment) => {
      if (buildingId !== undefined) {
        if (payment.lease?.apartment?.building?.id !== buildingId) return false;
      }

      if (apartmentId !== undefined) {
        if (payment.lease?.apartment?.id !== apartmentId) return false;
      }

      if (monthFrom) {
        const from = monthFrom + '-01';
        if (payment.reference_month < from) return false;
      }

      if (monthTo) {
        const refPrefix = payment.reference_month.substring(0, 7);
        if (refPrefix > monthTo) return false;
      }

      return true;
    });
  }, [allPayments, buildingId, apartmentId, monthFrom, monthTo]);

  const hasActiveFilters =
    buildingId !== undefined ||
    apartmentId !== undefined ||
    monthFrom !== '' ||
    monthTo !== '';

  const clearFilters = useCallback(() => {
    setBuildingId(undefined);
    setApartmentId(undefined);
    setMonthFrom('');
    setMonthTo('');
  }, []);

  const handleDelete = useCallback(
    (payment: RentPayment) => {
      crud.setItemToDelete(payment);
      if (payment.id !== undefined) crud.handleDeleteClick(payment.id);
    },
    [crud],
  );

  const columns: Column<RentPayment>[] = useMemo(
    () => [
      {
        title: 'Mês Ref.',
        key: 'reference_month',
        render: (_, record) => formatReferenceMonth(record.reference_month),
        sorter: (a: RentPayment, b: RentPayment) =>
          a.reference_month.localeCompare(b.reference_month),
      },
      {
        title: 'Apartamento',
        key: 'apartment',
        render: (_, record) => {
          const apt = record.lease?.apartment;
          if (!apt) return '-';
          const buildingName = apt.building?.name ?? '';
          return `${apt.number} - ${buildingName}`;
        },
        sorter: (a: RentPayment, b: RentPayment) => {
          const aptA = a.lease?.apartment?.number ?? 0;
          const aptB = b.lease?.apartment?.number ?? 0;
          return aptA - aptB;
        },
      },
      {
        title: 'Inquilino',
        key: 'tenant',
        render: (_, record) => record.lease?.responsible_tenant?.name ?? '-',
      },
      {
        title: 'Valor Pago',
        key: 'amount_paid',
        render: (_, record) => formatCurrency(record.amount_paid),
        sorter: (a: RentPayment, b: RentPayment) =>
          a.amount_paid - b.amount_paid,
      },
      {
        title: 'Data Pgto.',
        key: 'payment_date',
        render: (_, record) => formatDate(record.payment_date),
        sorter: (a: RentPayment, b: RentPayment) =>
          a.payment_date.localeCompare(b.payment_date),
      },
      ...(isAdmin
        ? [
            {
              title: 'Ações',
              key: 'actions',
              width: 120,
              fixed: 'right' as const,
              render: (_: unknown, record: RentPayment) => (
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

  if (error) {
    toast.error('Erro ao carregar pagamentos de aluguel');
  }

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Pagamentos de Aluguel</h1>
          <p className="text-muted-foreground mt-1">
            Gerencie os pagamentos de aluguel recebidos
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => filteredPayments.length > 0 && exportToExcel(filteredPayments as Record<string, unknown>[], rentPaymentExportColumns, { filename: 'pagamentos_aluguel' })}
            disabled={isExporting || filteredPayments.length === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            Exportar
          </Button>
          {isAdmin && (
            <Button onClick={crud.openCreateModal}>
              <Plus className="h-4 w-4 mr-2" />
              Registrar Pagamento
            </Button>
          )}
        </div>
      </div>

      <Card className="mb-4 p-4">
        <div className="flex gap-4 flex-wrap items-end">
          <div className="flex-1 min-w-[180px]">
            <label className="block text-sm font-medium mb-2">Prédio</label>
            <Select
              value={buildingId !== undefined ? String(buildingId) : 'all'}
              onValueChange={(value) => {
                setBuildingId(value === 'all' ? undefined : Number(value));
                setApartmentId(undefined);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Todos os prédios" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos os prédios</SelectItem>
                {buildings?.map((b) => (
                  <SelectItem key={b.id} value={String(b.id)}>
                    {b.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 min-w-[180px]">
            <label className="block text-sm font-medium mb-2">
              Apartamento
            </label>
            <Select
              value={apartmentId !== undefined ? String(apartmentId) : 'all'}
              onValueChange={(value) =>
                setApartmentId(value === 'all' ? undefined : Number(value))
              }
              disabled={buildingId === undefined}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    buildingId === undefined
                      ? 'Selecione um prédio'
                      : 'Todos os apartamentos'
                  }
                />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos os apartamentos</SelectItem>
                {apartments?.map((apt) => (
                  <SelectItem key={apt.id} value={String(apt.id)}>
                    Apt {apt.number}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 min-w-[160px]">
            <label className="block text-sm font-medium mb-2">Mês de</label>
            <Input
              type="month"
              value={monthFrom}
              onChange={(e) => setMonthFrom(e.target.value)}
            />
          </div>

          <div className="flex-1 min-w-[160px]">
            <label className="block text-sm font-medium mb-2">Mês até</label>
            <Input
              type="month"
              value={monthTo}
              onChange={(e) => setMonthTo(e.target.value)}
            />
          </div>

          {hasActiveFilters && (
            <Button variant="outline" onClick={clearFilters}>
              Limpar Filtros
            </Button>
          )}
        </div>
      </Card>

      <DataTable<RentPayment>
        columns={columns}
        dataSource={filteredPayments}
        loading={isLoading}
        rowKey="id"
      />

      <RentPaymentFormModal
        open={crud.isModalOpen}
        rentPayment={crud.editingItem}
        onClose={crud.closeModal}
      />

      <DeleteConfirmDialog
        open={crud.deleteDialogOpen}
        onOpenChange={crud.setDeleteDialogOpen}
        itemName={
          crud.itemToDelete
            ? formatReferenceMonth(crud.itemToDelete.reference_month)
            : undefined
        }
        onConfirm={crud.handleDelete}
        isLoading={crud.isDeleting}
      />
    </div>
  );
}
