'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Plus, Pencil, Trash2, Loader2, CheckCircle2, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { DataTable, type Column } from '@/components/tables/data-table';
import { DeleteConfirmDialog } from '@/components/shared/delete-confirm-dialog';
import { cn } from '@/lib/utils';
import { useIncomeEntries, useDeleteIncomeEntry } from '@/lib/api/hooks/use-income-entries';
import type { IncomeEntryFilters } from '@/lib/schemas/finances/income-entry.schema';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useFinanceCategories } from '@/lib/api/hooks/use-finance-categories';
import { useAuthStore } from '@/store/auth-store';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';
import type { IncomeEntry } from '@/lib/schemas/finances/income-entry.schema';

function ModalLoader() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-background/80">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

const IncomeEntryFormModal = dynamic(
  () =>
    import('./_components/income-entry-form-modal').then((mod) => mod.IncomeEntryFormModal),
  { loading: () => <ModalLoader />, ssr: false },
);

function createColumns(handlers: {
  onEdit: (e: IncomeEntry) => void;
  onDelete: (e: IncomeEntry) => void;
  isDeleting: boolean;
  isStaff: boolean;
}): Column<IncomeEntry>[] {
  return [
    {
      title: 'Descrição',
      dataIndex: 'description',
      key: 'description',
      sorter: (a, b) => a.description.localeCompare(b.description),
    },
    {
      title: 'Valor',
      key: 'amount',
      width: 130,
      render: (_, rec) => formatCurrency(rec.amount),
    },
    {
      title: 'Data',
      key: 'income_date',
      width: 110,
      render: (_, rec) => formatDate(rec.income_date),
    },
    {
      title: 'Prédio',
      key: 'building',
      width: 140,
      render: (_, rec) => rec.building?.name ?? 'Condomínio',
    },
    {
      title: 'Categoria',
      key: 'category',
      width: 130,
      render: (_, rec) => {
        if (!rec.category) return <span className="text-muted-foreground">-</span>;
        return (
          <Badge
            style={{ backgroundColor: `${rec.category.color}20`, color: rec.category.color }}
          >
            {rec.category.name}
          </Badge>
        );
      },
    },
    {
      title: 'Status',
      key: 'is_received',
      width: 110,
      render: (_, rec) => (
        <Badge
          className={cn(
            'inline-flex items-center gap-1',
            rec.is_received ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning',
          )}
        >
          {rec.is_received ? <CheckCircle2 className="h-3 w-3" /> : <Clock className="h-3 w-3" />}
          {rec.is_received ? 'Recebido' : 'Pendente'}
        </Badge>
      ),
    },
    ...(handlers.isStaff
      ? [
          {
            title: 'Ações',
            key: 'actions',
            width: 120,
            fixed: 'right' as const,
            isActions: true,
            render: (_: unknown, rec: IncomeEntry) => (
              <div className="flex gap-1">
                <Button variant="ghost" size="icon" aria-label="Editar" onClick={() => handlers.onEdit(rec)}>
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Excluir"
                  onClick={() => handlers.onDelete(rec)}
                  disabled={handlers.isDeleting}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ),
          },
        ]
      : []),
  ];
}

export default function IncomeEntriesPage() {
  const { user } = useAuthStore();
  const isStaff = user?.is_staff ?? false;

  const [filters, setFilters] = useState<IncomeEntryFilters>({});
  const { data: entries, isLoading, error } = useIncomeEntries(filters);
  const { data: buildings } = useBuildings();
  const { data: categories } = useFinanceCategories();
  const deleteMutation = useDeleteIncomeEntry();

  const crud = useCrudPage<IncomeEntry>({
    entityName: 'receita',
    entityNamePlural: 'receitas',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir receita.',
  });

  const handleDelete = useCallback(
    (entry: IncomeEntry) => {
      crud.setItemToDelete(entry);
      if (entry.id !== undefined) crud.handleDeleteClick(entry.id);
    },
    [crud],
  );

  const columns = useMemo(
    () =>
      createColumns({
        onEdit: crud.openEditModal,
        onDelete: handleDelete,
        isDeleting: crud.isDeleting,
        isStaff,
      }),
    [crud.openEditModal, handleDelete, crud.isDeleting, isStaff],
  );

  const hasActiveFilters = Object.values(filters).some((v) => v !== undefined && v !== '');

  const clearFilters = () => {
    setFilters({ building_id: undefined, category_id: undefined, is_received: undefined, date_from: undefined, date_to: undefined });
  };

  useEffect(() => {
    if (error) toast.error('Erro ao carregar receitas do condomínio');
  }, [error]);

  return (
    <div>
      <div className="mb-4 flex justify-between items-center flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Receitas do Condomínio</h1>
          <p className="text-muted-foreground mt-1">Receitas e entradas financeiras</p>
        </div>
        {isStaff && (
          <Button onClick={crud.openCreateModal}>
            <Plus className="h-4 w-4 mr-2" />
            Nova Receita
          </Button>
        )}
      </div>

      {/* Filters */}
      <Card className="mb-4">
        <CardContent className="pt-6">
          <div className="flex gap-4 flex-wrap items-end">
            <div className="flex-1 min-w-[140px]">
              <label className="block text-sm font-medium mb-2">Prédio</label>
              <Select
                value={filters.building_id ? String(filters.building_id) : 'all'}
                onValueChange={(v) =>
                  setFilters({ ...filters, building_id: v === 'all' ? undefined : Number(v) })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {buildings?.map((b) => (
                    <SelectItem key={b.id} value={String(b.id)}>
                      {b.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 min-w-[140px]">
              <label className="block text-sm font-medium mb-2">Categoria</label>
              <Select
                value={filters.category_id ? String(filters.category_id) : 'all'}
                onValueChange={(v) =>
                  setFilters({ ...filters, category_id: v === 'all' ? undefined : Number(v) })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todas" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  {categories?.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 min-w-[130px]">
              <label className="block text-sm font-medium mb-2">Status</label>
              <Select
                value={
                  filters.is_received === undefined
                    ? 'all'
                    : filters.is_received
                      ? 'received'
                      : 'pending'
                }
                onValueChange={(v) =>
                  setFilters({
                    ...filters,
                    is_received: v === 'all' ? undefined : v === 'received',
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

            <div className="flex-1 min-w-[140px]">
              <label className="block text-sm font-medium mb-2">Data início</label>
              <Input
                type="date"
                value={filters.date_from ?? ''}
                onChange={(e) => setFilters({ ...filters, date_from: e.target.value || undefined })}
              />
            </div>

            <div className="flex-1 min-w-[140px]">
              <label className="block text-sm font-medium mb-2">Data fim</label>
              <Input
                type="date"
                value={filters.date_to ?? ''}
                onChange={(e) => setFilters({ ...filters, date_to: e.target.value || undefined })}
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

      <DataTable<IncomeEntry>
        columns={columns}
        dataSource={entries}
        loading={isLoading}
        rowKey="id"
      />

      <IncomeEntryFormModal
        open={crud.isModalOpen}
        entry={crud.editingItem}
        onClose={crud.closeModal}
      />

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
