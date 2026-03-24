'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { DataTable, type Column } from '@/components/tables/data-table';
import { DeleteConfirmDialog } from '@/components/shared/delete-confirm-dialog';
import { CategoryFormModal } from './_components/category-form-modal';
import {
  useExpenseCategories,
  useDeleteExpenseCategory,
} from '@/lib/api/hooks/use-expense-categories';
import { type ExpenseCategory } from '@/lib/schemas/expense-category.schema';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import { useAuthStore } from '@/store/auth-store';

interface FlatCategory {
  [key: string]: unknown;
  id?: number;
  name: string;
  description?: string;
  color?: string;
  parent_name: string;
  depth: number;
  parent_id?: number | null;
}

function flattenCategories(categories: ExpenseCategory[]): FlatCategory[] {
  const result: FlatCategory[] = [];
  for (const cat of categories) {
    if (!cat.parent) {
      result.push({
        id: cat.id,
        name: cat.name,
        description: cat.description,
        color: cat.color,
        parent_name: '',
        depth: 0,
        parent_id: null,
      });
      if (cat.subcategories) {
        for (const sub of cat.subcategories) {
          result.push({
            id: sub.id,
            name: sub.name,
            description: sub.description,
            color: sub.color,
            parent_name: cat.name,
            depth: 1,
            parent_id: cat.id,
          });
        }
      }
    }
  }
  return result;
}

export default function CategoriesPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;
  const { data: categories, isLoading, error } = useExpenseCategories();
  const deleteMutation = useDeleteExpenseCategory();

  const crud = useCrudPage<ExpenseCategory>({
    entityName: 'categoria',
    entityNamePlural: 'categorias',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir categoria. Verifique se não há despesas vinculadas.',
  });

  const flatCategories = flattenCategories(categories ?? []);

  const findOriginalCategory = (id: number | undefined): ExpenseCategory | null => {
    if (!id || !categories) return null;
    for (const cat of categories) {
      if (cat.id === id) return cat;
      if (cat.subcategories) {
        for (const sub of cat.subcategories) {
          if (sub.id === id) return sub;
        }
      }
    }
    return null;
  };

  const columns: Column<FlatCategory>[] = [
    {
      title: 'Nome',
      dataIndex: 'name',
      key: 'name',
      render: (_, record) => (
        <span style={{ paddingLeft: record.depth * 24 }}>
          {record.depth > 0 && <span className="text-muted-foreground mr-2">└</span>}
          {record.name}
        </span>
      ),
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'Descrição',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'Cor',
      key: 'color',
      width: 80,
      render: (_, record) => (
        <div className="flex items-center gap-2">
          <div
            className="w-6 h-6 rounded border"
            style={{ backgroundColor: record.color ?? '#6B7280' }}
          />
        </div>
      ),
    },
    {
      title: 'Pai',
      key: 'parent_name',
      render: (_, record) => {
        if (!record.parent_name) return <span className="text-muted-foreground">—</span>;
        return <span>{record.parent_name}</span>;
      },
    },
    ...(isAdmin
      ? [
          {
            title: 'Ações',
            key: 'actions',
            width: 150,
            fixed: 'right' as const,
            render: (_: unknown, record: FlatCategory) => (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const original = findOriginalCategory(record.id);
                    if (original) crud.openEditModal(original);
                  }}
                >
                  <Pencil className="h-4 w-4 mr-1" />
                  Editar
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const original = findOriginalCategory(record.id);
                    if (original) {
                      crud.setItemToDelete(original);
                      if (record.id !== undefined) crud.handleDeleteClick(record.id);
                    }
                  }}
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
  ];

  useEffect(() => {
    if (error) toast.error('Erro ao carregar categorias');
  }, [error]);

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Categorias de Despesas</h1>
          <p className="text-muted-foreground mt-1">Gerencie as categorias e subcategorias de despesas</p>
        </div>
        {isAdmin && (
          <Button onClick={crud.openCreateModal}>
            <Plus className="h-4 w-4 mr-2" />
            Nova Categoria
          </Button>
        )}
      </div>

      <DataTable<FlatCategory>
        columns={columns}
        dataSource={flatCategories}
        loading={isLoading}
        rowKey="id"
      />

      <CategoryFormModal
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
