'use client';

import { useEffect } from 'react';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { DataTable, type Column } from '@/components/tables/data-table';
import { DeleteConfirmDialog } from '@/components/shared/delete-confirm-dialog';
import {
  useDeleteFinanceCategory,
  useFinanceCategories,
} from '@/lib/api/hooks/use-finance-categories';
import { type FinanceCategory } from '@/lib/schemas/finances/category.schema';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import { useAuthStore } from '@/store/auth-store';
import { FinanceCategoryFormModal } from './_components/finance-category-form-modal';

export default function FinanceCategoriesPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;
  const { data: categories, isLoading, error } = useFinanceCategories();
  const deleteMutation = useDeleteFinanceCategory();

  const crud = useCrudPage<FinanceCategory>({
    entityName: 'categoria',
    entityNamePlural: 'categorias',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir categoria. Verifique se não há contas vinculadas.',
  });

  useEffect(() => {
    if (error) toast.error('Erro ao carregar categorias');
  }, [error]);

  const columns: Column<FinanceCategory>[] = [
    {
      title: 'Nome',
      dataIndex: 'name',
      key: 'name',
      primary: true,
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'Cor',
      key: 'color',
      width: 80,
      render: (_, record) => (
        <div
          className="h-6 w-6 rounded border"
          style={{ backgroundColor: record.color || '#6B7280' }}
        />
      ),
    },
    {
      title: 'Ordem',
      key: 'sort_order',
      width: 100,
      render: (_, record) => record.sort_order ?? 0,
    },
    {
      title: 'Pai',
      key: 'parent',
      render: (_, record) =>
        record.parent ? record.parent.name : <span className="text-muted-foreground">—</span>,
    },
    ...(isAdmin
      ? [
          {
            title: 'Ações',
            key: 'actions',
            width: 150,
            fixed: 'right' as const,
            render: (_: unknown, record: FinanceCategory) => (
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => crud.openEditModal(record)}>
                  <Pencil className="mr-1 h-4 w-4" />
                  Editar
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    crud.setItemToDelete(record);
                    if (record.id !== undefined) crud.handleDeleteClick(record.id);
                  }}
                  disabled={crud.isDeleting}
                >
                  <Trash2 className="mr-1 h-4 w-4" />
                  Excluir
                </Button>
              </div>
            ),
          } satisfies Column<FinanceCategory>,
        ]
      : []),
  ];

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Categorias</h1>
          <p className="mt-1 text-muted-foreground">
            Classificação opcional das contas do condomínio (distinta do tipo de conta)
          </p>
        </div>
        {isAdmin && (
          <Button onClick={crud.openCreateModal}>
            <Plus className="mr-2 h-4 w-4" />
            Nova Categoria
          </Button>
        )}
      </div>

      {!isLoading && (categories?.length ?? 0) === 0 ? (
        <p className="rounded-md border-2 border-dashed py-12 text-center text-sm text-muted-foreground">
          Nenhuma categoria cadastrada
        </p>
      ) : (
        <DataTable<FinanceCategory>
          columns={columns}
          dataSource={categories}
          loading={isLoading}
          rowKey="id"
        />
      )}

      <FinanceCategoryFormModal
        open={crud.isModalOpen}
        category={crud.editingItem}
        onClose={crud.closeModal}
      />

      <DeleteConfirmDialog
        open={crud.deleteDialogOpen}
        onOpenChange={crud.setDeleteDialogOpen}
        itemName={crud.itemToDelete?.name}
        onConfirm={crud.handleDelete}
        isLoading={crud.isDeleting}
      />
    </div>
  );
}
