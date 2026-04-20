'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Plus, Pencil, Trash2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { DataTable, type Column } from '@/components/tables/data-table';
import { UserFormModal } from './_components/user-form-modal';
import { useAdminUsers, useDeleteAdminUser } from '@/lib/api/hooks/use-users';
import { useAuthStore } from '@/store/auth-store';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import type { AdminUser } from '@/lib/schemas/user';
import { formatDate } from '@/lib/utils/formatters';

export default function AdminUsersPage() {
  const router = useRouter();
  const { user: currentUser } = useAuthStore();
  const { data: users, isLoading, error } = useAdminUsers();
  const deleteMutation = useDeleteAdminUser();

  useEffect(() => {
    if (currentUser !== null && !currentUser?.is_staff) {
      router.replace('/');
    }
  }, [currentUser, router]);

  const crud = useCrudPage<AdminUser>({
    entityName: 'usuário',
    entityNamePlural: 'usuários',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir usuário.',
  });

  const columns: Column<AdminUser>[] = [
    {
      title: 'Usuário',
      dataIndex: 'username',
      key: 'username',
      sorter: (a, b) => a.username.localeCompare(b.username),
    },
    {
      title: 'Nome',
      key: 'full_name',
      render: (_, record) =>
        [record.first_name, record.last_name].filter(Boolean).join(' ') || '-',
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Admin',
      key: 'is_staff',
      render: (_, record) =>
        record.is_staff ? (
          <Badge variant="default">Sim</Badge>
        ) : (
          <Badge variant="secondary">Não</Badge>
        ),
      width: 80,
    },
    {
      title: 'Ativo',
      key: 'is_active',
      render: (_, record) =>
        record.is_active ? (
          <Badge variant="default">Sim</Badge>
        ) : (
          <Badge variant="destructive">Não</Badge>
        ),
      width: 80,
    },
    {
      title: 'Criado em',
      key: 'date_joined',
      render: (_, record) => formatDate(record.date_joined),
      width: 120,
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => crud.openEditModal(record)}>
            <Pencil className="h-4 w-4 mr-1" />
            Editar
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
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
  ];

  if (error) {
    toast.error('Erro ao carregar usuários');
  }

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Usuários</h1>
          <p className="text-muted-foreground mt-1">Gerencie os usuários do sistema</p>
        </div>
        <Button onClick={crud.openCreateModal}>
          <Plus className="h-4 w-4 mr-2" />
          Novo Usuário
        </Button>
      </div>

      {error && !users && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erro</AlertTitle>
          <AlertDescription>
            Erro ao carregar dados. Verifique sua conexão e tente novamente.
          </AlertDescription>
        </Alert>
      )}

      <DataTable<AdminUser>
        columns={columns}
        dataSource={users}
        loading={isLoading}
        rowKey="id"
      />

      <UserFormModal open={crud.isModalOpen} user={crud.editingItem} onClose={crud.closeModal} />

      <AlertDialog open={crud.deleteDialogOpen} onOpenChange={crud.setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir usuário</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir este usuário? Esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={crud.handleDelete}
              disabled={crud.isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {crud.isDeleting ? 'Excluindo...' : 'Excluir'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
