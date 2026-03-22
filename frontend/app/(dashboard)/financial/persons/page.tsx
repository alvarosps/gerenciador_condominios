'use client';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { DataTable, type Column } from '@/components/tables/data-table';
import { DeleteConfirmDialog } from '@/components/shared/delete-confirm-dialog';
import { PersonFormModal } from './_components/person-form-modal';
import {
  usePersons,
  useDeletePerson,
} from '@/lib/api/hooks/use-persons';
import { type Person } from '@/lib/schemas/person.schema';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import { useAuthStore } from '@/store/auth-store';

export default function PersonsPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;
  const { data: persons, isLoading, error } = usePersons();
  const deleteMutation = useDeletePerson();

  const crud = useCrudPage<Person>({
    entityName: 'pessoa',
    entityNamePlural: 'pessoas',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir pessoa. Verifique se não há despesas ou cartões vinculados.',
  });

  const columns: Column<Person>[] = [
    {
      title: 'Nome',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'Relação',
      dataIndex: 'relationship',
      key: 'relationship',
    },
    {
      title: 'Telefone',
      dataIndex: 'phone',
      key: 'phone',
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Proprietário',
      key: 'is_owner',
      width: 120,
      align: 'center',
      render: (_, record) => (
        <Badge variant={record.is_owner ? 'default' : 'secondary'}>
          {record.is_owner ? 'Sim' : 'Não'}
        </Badge>
      ),
    },
    {
      title: 'Funcionário',
      key: 'is_employee',
      width: 120,
      align: 'center',
      render: (_, record) => (
        <Badge variant={record.is_employee ? 'default' : 'secondary'}>
          {record.is_employee ? 'Sim' : 'Não'}
        </Badge>
      ),
    },
    {
      title: 'Cartões',
      key: 'credit_cards_count',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <span>{record.credit_cards?.length ?? 0}</span>
      ),
    },
    ...(isAdmin
      ? [
          {
            title: 'Ações',
            key: 'actions',
            width: 150,
            fixed: 'right' as const,
            render: (_: unknown, record: Person) => (
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
                  onClick={() => {
                    crud.setItemToDelete(record);
                    if (record.id !== undefined) crud.handleDeleteClick(record.id);
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

  if (error) {
    toast.error('Erro ao carregar pessoas');
  }

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Pessoas</h1>
          <p className="text-gray-600 mt-1">Gerencie pessoas, proprietários e seus cartões de crédito</p>
        </div>
        {isAdmin && (
          <Button onClick={crud.openCreateModal}>
            <Plus className="h-4 w-4 mr-2" />
            Nova Pessoa
          </Button>
        )}
      </div>

      <DataTable<Person>
        columns={columns}
        dataSource={persons}
        loading={isLoading}
        rowKey="id"
      />

      <PersonFormModal
        open={crud.isModalOpen}
        person={crud.editingItem}
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
