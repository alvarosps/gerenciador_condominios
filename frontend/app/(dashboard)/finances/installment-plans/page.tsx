'use client';

import { useState } from 'react';
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { DataTable } from '@/components/tables/data-table';
import {
  useDeleteInstallmentPlan,
  useInstallmentPlans,
} from '@/lib/api/hooks/use-installment-plans';
import { useAuthStore } from '@/store/auth-store';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import type { InstallmentPlan } from '@/lib/schemas/finances/installment-plan.schema';
import { buildInstallmentPlanColumns } from './_components/installment-plan-columns';
import { InstallmentPlanFormModal } from './_components/installment-plan-form-modal';
import { InstallmentScheduleField } from './_components/installment-schedule-field';
import { ConvertDeferredDialog } from './_components/convert-deferred-dialog';

export default function InstallmentPlansPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const [convertingPlan, setConvertingPlan] = useState<InstallmentPlan | null>(null);
  const [schedulePlan, setSchedulePlan] = useState<InstallmentPlan | null>(null);

  const { data: plans, isLoading } = useInstallmentPlans();
  const deleteMutation = useDeleteInstallmentPlan();

  const crud = useCrudPage<InstallmentPlan>({
    entityName: 'plano de parcelas',
    entityNamePlural: 'planos de parcelas',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir plano de parcelas.',
  });

  const columns = buildInstallmentPlanColumns({
    isAdmin,
    onViewSchedule: (plan) => {
      setSchedulePlan(plan);
    },
    onEdit: (plan) => crud.openEditModal(plan),
    onConvert: (plan) => {
      setConvertingPlan(plan);
    },
    onDelete: (plan) => {
      crud.setItemToDelete(plan);
      if (plan.id !== undefined) crud.handleDeleteClick(plan.id);
    },
  });

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Planos de Parcelas</h1>
          <p className="mt-1 text-muted-foreground">
            Gerencie os planos de parcelas do condomínio (IPTU, parcelamentos)
          </p>
        </div>
        {isAdmin && (
          <Button onClick={crud.openCreateModal}>
            <Plus className="mr-2 h-4 w-4" />
            Novo Plano
          </Button>
        )}
      </div>

      {!isLoading && (plans?.length ?? 0) === 0 ? (
        <p className="rounded-md border-2 border-dashed py-12 text-center text-sm text-muted-foreground">
          Nenhum plano de parcelas cadastrado
        </p>
      ) : (
        <DataTable<InstallmentPlan>
          columns={columns}
          dataSource={plans}
          loading={isLoading}
          rowKey="id"
        />
      )}

      <InstallmentPlanFormModal
        open={crud.isModalOpen}
        plan={crud.editingItem}
        onClose={crud.closeModal}
      />

      <ConvertDeferredDialog
        open={convertingPlan !== null}
        billId={convertingPlan?.id ?? null}
        description={convertingPlan?.description}
        onClose={() => {
          setConvertingPlan(null);
        }}
      />

      <Sheet
        open={schedulePlan !== null}
        onOpenChange={(open) => {
          if (!open) setSchedulePlan(null);
        }}
      >
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>Cronograma de Parcelas</SheetTitle>
            <SheetDescription>{schedulePlan?.description ?? ''}</SheetDescription>
          </SheetHeader>
          <div className="mt-4">
            <InstallmentScheduleField
              installments={schedulePlan?.installments ?? []}
              isAdmin={isAdmin}
            />
          </div>
        </SheetContent>
      </Sheet>

      <AlertDialog open={crud.deleteDialogOpen} onOpenChange={crud.setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir plano de parcelas</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir{' '}
              {crud.itemToDelete?.description
                ? `"${crud.itemToDelete.description}"`
                : 'este plano'}
              ? Esta ação não pode ser desfeita.
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
