'use client';

import { useState, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Plus, Loader2, Pencil, Trash2, CheckCircle, Download } from 'lucide-react';
import { toast } from 'sonner';
import { DataTable, type Column } from '@/components/tables/data-table';
import { DeleteConfirmDialog } from '@/components/shared/delete-confirm-dialog';
import { cn } from '@/lib/utils';
import {
  useIncomes,
  useDeleteIncome,
  useMarkIncomeReceived,
  type IncomeFilters,
} from '@/lib/api/hooks/use-incomes';
import { usePersons } from '@/lib/api/hooks/use-persons';
import { type Income } from '@/lib/schemas/income.schema';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import { useExport, incomeExportColumns } from '@/lib/hooks/use-export';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';

interface ExtendedIncomeFilters extends IncomeFilters {
  date_from?: string;
  date_to?: string;
}

function ModalLoader() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-background/80">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

const IncomeFormModal = dynamic(
  () => import('./_components/income-form-modal').then((mod) => mod.IncomeFormModal),
  { loading: () => <ModalLoader />, ssr: false },
);

interface IncomeActionHandlers {
  onEdit: (income: Income) => void;
  onDelete: (income: Income) => void;
  onMarkReceived: (income: Income) => void | Promise<void>;
  isDeleting: boolean;
  isMarkingReceived: boolean;
}

function createIncomeColumns(handlers: IncomeActionHandlers): Column<Income>[] {
  return [
    {
      title: 'Descrição',
      dataIndex: 'description',
      key: 'description',
      sorter: (a, b) => a.description.localeCompare(b.description),
    },
    {
      title: 'Valor',
      dataIndex: 'amount',
      key: 'amount',
      width: 130,
      render: (value) => formatCurrency(value as number),
      sorter: (a, b) => a.amount - b.amount,
    },
    {
      title: 'Data',
      dataIndex: 'income_date',
      key: 'income_date',
      width: 110,
      render: (value) => formatDate(value as string),
      sorter: (a, b) => new Date(a.income_date).getTime() - new Date(b.income_date).getTime(),
    },
    {
      title: 'Pessoa',
      key: 'person',
      width: 140,
      render: (_, record) => record.person?.name ?? '-',
    },
    {
      title: 'Prédio',
      key: 'building',
      width: 130,
      render: (_, record) => record.building?.name ?? '-',
    },
    {
      title: 'Categoria',
      key: 'category',
      width: 130,
      render: (_, record) => {
        if (!record.category) return '-';
        return (
          <Badge
            style={{ backgroundColor: `${record.category.color}20`, color: record.category.color }}
          >
            {record.category.name}
          </Badge>
        );
      },
    },
    {
      title: 'Recorrente',
      key: 'is_recurring',
      width: 110,
      align: 'center',
      render: (_, record) => (
        <Badge className={cn(record.is_recurring ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground')}>
          {record.is_recurring ? 'Sim' : 'Não'}
        </Badge>
      ),
    },
    {
      title: 'Recebido',
      key: 'is_received',
      width: 110,
      align: 'center',
      render: (_, record) => (
        <Badge className={cn(record.is_received ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning')}>
          {record.is_received ? 'Recebido' : 'Pendente'}
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

            {!record.is_received && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Marcar como Recebido"
                    onClick={() => void handlers.onMarkReceived(record)}
                    disabled={handlers.isMarkingReceived}
                  >
                    <CheckCircle className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Marcar como Recebido</TooltipContent>
              </Tooltip>
            )}
          </div>
        </TooltipProvider>
      ),
    },
  ];
}

export default function IncomesPage() {
  const [filters, setFilters] = useState<ExtendedIncomeFilters>({});

  const { data: incomes, isLoading, error } = useIncomes(filters);
  const { data: persons } = usePersons();
  const deleteMutation = useDeleteIncome();
  const { exportToExcel, isExporting } = useExport();
  const markReceivedMutation = useMarkIncomeReceived();

  const crud = useCrudPage<Income>({
    entityName: 'receita',
    entityNamePlural: 'receitas',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir receita.',
  });

  const handleDelete = useCallback(
    (income: Income) => {
      crud.setItemToDelete(income);
      if (income.id !== undefined) crud.handleDeleteClick(income.id);
    },
    [crud],
  );

  const handleMarkReceived = useCallback(
    async (income: Income) => {
      if (income.id === undefined) return;
      try {
        await markReceivedMutation.mutateAsync(income.id);
        toast.success('Receita marcada como recebida');
      } catch {
        toast.error('Erro ao marcar receita como recebida');
      }
    },
    [markReceivedMutation],
  );

  const columns = useMemo(
    () =>
      createIncomeColumns({
        onEdit: crud.openEditModal,
        onDelete: handleDelete,
        onMarkReceived: handleMarkReceived,
        isDeleting: crud.isDeleting,
        isMarkingReceived: markReceivedMutation.isPending,
      }),
    [crud.openEditModal, crud.isDeleting, handleDelete, handleMarkReceived, markReceivedMutation.isPending],
  );

  const hasActiveFilters = Object.entries(filters).some(([, v]) => v !== undefined && v !== '');

  const clearFilters = () => {
    setFilters({
      person_id: undefined,
      is_recurring: undefined,
      is_received: undefined,
      date_from: undefined,
      date_to: undefined,
    });
  };

  if (error) {
    toast.error('Erro ao carregar receitas');
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Receitas</h1>
          <p className="text-muted-foreground mt-1">
            Gerencie receitas e recebimentos
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => incomes && exportToExcel(incomes as Record<string, unknown>[], incomeExportColumns, { filename: 'receitas' })}
            disabled={isExporting || !incomes?.length}
          >
            <Download className="h-4 w-4 mr-2" />
            Exportar
          </Button>
          <Button onClick={crud.openCreateModal}>
            <Plus className="h-4 w-4 mr-2" />
            Nova Receita
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="mb-4">
        <CardContent className="pt-6">
          <div className="flex gap-4 flex-wrap items-end">
            {/* Pessoa */}
            <div className="flex-1 min-w-[150px]">
              <label className="block text-sm font-medium mb-2">Pessoa</label>
              <Select
                value={filters.person_id ? String(filters.person_id) : 'all'}
                onValueChange={(value) =>
                  setFilters({
                    ...filters,
                    person_id: value === 'all' ? undefined : Number(value),
                  })
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

            {/* Recorrente */}
            <div className="flex-1 min-w-[130px]">
              <label className="block text-sm font-medium mb-2">Recorrente</label>
              <Select
                value={filters.is_recurring === undefined ? 'all' : filters.is_recurring ? 'true' : 'false'}
                onValueChange={(value) =>
                  setFilters({
                    ...filters,
                    is_recurring: value === 'all' ? undefined : value === 'true',
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="true">Sim</SelectItem>
                  <SelectItem value="false">Não</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Recebido */}
            <div className="flex-1 min-w-[130px]">
              <label className="block text-sm font-medium mb-2">Status</label>
              <Select
                value={filters.is_received === undefined ? 'all' : filters.is_received ? 'received' : 'pending'}
                onValueChange={(value) =>
                  setFilters({
                    ...filters,
                    is_received: value === 'all' ? undefined : value === 'received',
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="received">Recebido</SelectItem>
                  <SelectItem value="pending">Pendente</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Data início */}
            <div className="flex-1 min-w-[140px]">
              <label className="block text-sm font-medium mb-2">Data início</label>
              <Input
                type="date"
                value={filters.date_from ?? ''}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    date_from: e.target.value || undefined,
                  })
                }
              />
            </div>

            {/* Data fim */}
            <div className="flex-1 min-w-[140px]">
              <label className="block text-sm font-medium mb-2">Data fim</label>
              <Input
                type="date"
                value={filters.date_to ?? ''}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    date_to: e.target.value || undefined,
                  })
                }
              />
            </div>

            {hasActiveFilters && (
              <Button variant="outline" onClick={clearFilters}>
                Limpar Filtros
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Data Table */}
      <DataTable<Income>
        columns={columns}
        dataSource={incomes}
        loading={isLoading}
        rowKey="id"
      />

      {/* Form Modal */}
      <IncomeFormModal
        open={crud.isModalOpen}
        income={crud.editingItem}
        onClose={crud.closeModal}
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
