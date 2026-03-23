'use client';

import { useState, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
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
  usePersonIncomes,
  useDeletePersonIncome,
  type PersonIncomeFilters,
} from '@/lib/api/hooks/use-person-incomes';
import { usePersons } from '@/lib/api/hooks/use-persons';
import type { PersonIncome } from '@/lib/schemas/person-income.schema';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import { useAuthStore } from '@/store/auth-store';

function ModalLoader() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-background/80">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

const PersonIncomeFormModal = dynamic(
  () =>
    import('./_components/person-income-form-modal').then(
      (mod) => mod.PersonIncomeFormModal,
    ),
  { loading: () => <ModalLoader />, ssr: false },
);

const INCOME_TYPE_LABELS: Record<string, string> = {
  apartment_rent: 'Aluguel Apartamento',
  fixed_stipend: 'Estipêndio Fixo',
};

function getIncomeTypeLabel(type: string): string {
  return INCOME_TYPE_LABELS[type] ?? type;
}

function getIncomeValue(record: PersonIncome): string {
  if (record.income_type === 'fixed_stipend') {
    return record.fixed_amount !== null && record.fixed_amount !== undefined
      ? formatCurrency(record.fixed_amount)
      : '-';
  }
  if (record.current_value !== undefined) {
    return formatCurrency(record.current_value);
  }
  return 'Sem lease';
}

function getApartmentLabel(record: PersonIncome): string {
  if (record.income_type !== 'apartment_rent') return '-';
  if (!record.apartment) return '-';
  const apt = record.apartment;
  const buildingName = apt.building?.name ?? apt.building?.street_number ?? '';
  return `Apto ${apt.number}/${buildingName}`;
}

export default function PersonIncomesPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const [filterPersonId, setFilterPersonId] = useState<number | undefined>(undefined);
  const [filterIncomeType, setFilterIncomeType] = useState<string | undefined>(undefined);
  const [filterIsActive, setFilterIsActive] = useState<boolean | undefined>(undefined);

  const filters: PersonIncomeFilters = useMemo(
    () => ({
      person_id: filterPersonId,
      income_type: filterIncomeType,
      is_active: filterIsActive,
    }),
    [filterPersonId, filterIncomeType, filterIsActive],
  );

  const { data: persons } = usePersons();
  const { data: personIncomes, isLoading, error } = usePersonIncomes(filters);
  const deleteMutation = useDeletePersonIncome();

  const crud = useCrudPage<PersonIncome>({
    entityName: 'rendimento',
    entityNamePlural: 'rendimentos',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir rendimento.',
  });

  const handleDelete = useCallback(
    (record: PersonIncome) => {
      crud.setItemToDelete(record);
      if (record.id !== undefined) crud.handleDeleteClick(record.id);
    },
    [crud],
  );

  const columns: Column<PersonIncome>[] = useMemo(
    () => [
      {
        title: 'Pessoa',
        key: 'person',
        render: (_, record) => {
          const name = record.person?.name ?? '-';
          const relationship = record.person?.relationship;
          return (
            <div className="flex items-center gap-2">
              <span>{name}</span>
              {relationship && (
                <Badge variant="outline" className="text-xs">
                  {relationship}
                </Badge>
              )}
            </div>
          );
        },
        sorter: (a: PersonIncome, b: PersonIncome) =>
          (a.person?.name ?? '').localeCompare(b.person?.name ?? ''),
      },
      {
        title: 'Tipo',
        key: 'income_type',
        render: (_, record) => (
          <Badge variant={record.income_type === 'apartment_rent' ? 'default' : 'secondary'}>
            {getIncomeTypeLabel(record.income_type)}
          </Badge>
        ),
      },
      {
        title: 'Apartamento',
        key: 'apartment',
        render: (_, record) => getApartmentLabel(record),
      },
      {
        title: 'Valor',
        key: 'value',
        render: (_, record) => getIncomeValue(record),
        sorter: (a: PersonIncome, b: PersonIncome) => {
          const valA = a.income_type === 'fixed_stipend' ? (a.fixed_amount ?? 0) : (a.current_value ?? 0);
          const valB = b.income_type === 'fixed_stipend' ? (b.fixed_amount ?? 0) : (b.current_value ?? 0);
          return valA - valB;
        },
      },
      {
        title: 'Vigência',
        key: 'dates',
        render: (_, record) => {
          const start = formatDate(record.start_date);
          const end = record.end_date ? formatDate(record.end_date) : 'Indefinido';
          return `${start} — ${end}`;
        },
      },
      {
        title: 'Ativo',
        key: 'is_active',
        width: 80,
        align: 'center',
        render: (_, record) => (
          <Badge variant={record.is_active ? 'default' : 'secondary'}>
            {record.is_active ? 'Sim' : 'Não'}
          </Badge>
        ),
      },
      ...(isAdmin
        ? [
            {
              title: 'Ações',
              key: 'actions',
              width: 150,
              fixed: 'right' as const,
              render: (_: unknown, record: PersonIncome) => (
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
    toast.error('Erro ao carregar rendimentos');
  }

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Rendimentos por Pessoa</h1>
          <p className="text-gray-600 mt-1">
            Gerencie o que cada pessoa tem direito a receber mensalmente
          </p>
        </div>
        {isAdmin && (
          <Button onClick={crud.openCreateModal}>
            <Plus className="h-4 w-4 mr-2" />
            Novo Rendimento
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
                {persons?.map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 min-w-[180px]">
            <label className="block text-sm font-medium mb-2">Tipo</label>
            <Select
              value={filterIncomeType ?? 'all'}
              onValueChange={(value) =>
                setFilterIncomeType(value === 'all' ? undefined : value)
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Todos os tipos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="apartment_rent">Aluguel</SelectItem>
                <SelectItem value="fixed_stipend">Estipêndio</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 min-w-[140px]">
            <label className="block text-sm font-medium mb-2">Status</label>
            <Select
              value={filterIsActive === undefined ? 'all' : filterIsActive ? 'active' : 'inactive'}
              onValueChange={(value) => {
                if (value === 'all') setFilterIsActive(undefined);
                else if (value === 'active') setFilterIsActive(true);
                else setFilterIsActive(false);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="active">Ativos</SelectItem>
                <SelectItem value="inactive">Inativos</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      <DataTable<PersonIncome>
        columns={columns}
        dataSource={personIncomes}
        loading={isLoading}
        rowKey="id"
      />

      <PersonIncomeFormModal
        open={crud.isModalOpen}
        personIncome={crud.editingItem}
        onClose={crud.closeModal}
      />

      <DeleteConfirmDialog
        open={crud.deleteDialogOpen}
        onOpenChange={crud.setDeleteDialogOpen}
        itemName={
          crud.itemToDelete
            ? `${crud.itemToDelete.person?.name ?? 'Rendimento'} - ${getIncomeTypeLabel(crud.itemToDelete.income_type)}`
            : undefined
        }
        onConfirm={crud.handleDelete}
        isLoading={crud.isDeleting}
      />
    </div>
  );
}
