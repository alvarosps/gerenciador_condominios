'use client';

import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
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
import { DataTable } from '@/components/tables/data-table';
import { useDeleteEmployee, useEmployees } from '@/lib/api/hooks/use-employees';
import { useAuthStore } from '@/store/auth-store';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import type { Employee } from '@/lib/schemas/finances/employee.schema';
import { buildEmployeeColumns } from './_components/employee-columns';
import { EmployeeFormModal } from './_components/employee-form-modal';

export default function EmployeesPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const { data: employees, isLoading } = useEmployees();
  const deleteMutation = useDeleteEmployee();

  const crud = useCrudPage<Employee>({
    entityName: 'funcionário',
    entityNamePlural: 'funcionários',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir funcionário.',
  });

  const columns = buildEmployeeColumns({
    isAdmin,
    onEdit: (employee) => crud.openEditModal(employee),
    onDelete: (employee) => {
      crud.setItemToDelete(employee);
      if (employee.id !== undefined) crud.handleDeleteClick(employee.id);
    },
  });

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Folha de Pagamento</h1>
          <p className="mt-1 text-muted-foreground">
            Gerencie os funcionários do condomínio e seus pagamentos
          </p>
        </div>
        {isAdmin && (
          <Button onClick={crud.openCreateModal}>
            <Plus className="mr-2 h-4 w-4" />
            Novo Funcionário
          </Button>
        )}
      </div>

      {!isLoading && (employees?.length ?? 0) === 0 ? (
        <p className="rounded-md border-2 border-dashed py-12 text-center text-sm text-muted-foreground">
          Nenhum funcionário cadastrado
        </p>
      ) : (
        <DataTable<Employee>
          columns={columns}
          dataSource={employees}
          loading={isLoading}
          rowKey="id"
        />
      )}

      <EmployeeFormModal
        open={crud.isModalOpen}
        employee={crud.editingItem}
        onClose={crud.closeModal}
      />

      <AlertDialog open={crud.deleteDialogOpen} onOpenChange={crud.setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir funcionário</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir{' '}
              {crud.itemToDelete?.name ? `"${crud.itemToDelete.name}"` : 'este funcionário'}? Esta
              ação não pode ser desfeita.
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
