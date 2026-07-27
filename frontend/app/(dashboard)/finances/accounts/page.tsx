'use client';

import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DataTable } from '@/components/tables/data-table';
import { DeleteConfirmDialog } from '@/components/shared/delete-confirm-dialog';
import { PageHeader } from '@/components/layouts/page-header';
import { useBillingAccounts, useDeleteBillingAccount } from '@/lib/api/hooks/use-billing-accounts';
import type { BillingAccountFilters } from '@/lib/api/hooks/use-billing-accounts';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import { useAuthStore } from '@/store/auth-store';
import {
  ACCOUNT_TYPE_LABELS,
  billingAccountTypeValues,
  type BillingAccount,
} from '@/lib/schemas/finances/billing-account.schema';
import { buildAccountColumns } from './_components/account-columns';
import { AccountFormModal } from './_components/account-form-modal';

const ALL = 'all';

export default function AccountsPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const [buildingFilter, setBuildingFilter] = useState<string>(ALL);
  const [typeFilter, setTypeFilter] = useState<string>(ALL);

  const { data: buildings } = useBuildings();

  const filters: BillingAccountFilters = {
    ...(buildingFilter === ALL ? {} : { building_id: Number(buildingFilter) }),
    ...(typeFilter === ALL ? {} : { account_type: typeFilter }),
  };

  const { data: accounts, isLoading } = useBillingAccounts(filters);
  const deleteMutation = useDeleteBillingAccount();

  const crud = useCrudPage<BillingAccount>({
    entityName: 'conta cadastrada',
    entityNamePlural: 'contas cadastradas',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir conta. Verifique se não há faturas vinculadas.',
  });

  const columns = buildAccountColumns({
    isAdmin,
    onEdit: (account) => crud.openEditModal(account),
    onDelete: (account) => {
      crud.setItemToDelete(account);
      if (account.id !== undefined) crud.handleDeleteClick(account.id);
    },
  });

  return (
    <div>
      <PageHeader
        title="Contas cadastradas"
        description="Registro das contas do condomínio (água, luz, IPTU, internet…)"
        actions={
          isAdmin && (
            <Button onClick={crud.openCreateModal}>
              <Plus className="mr-2 h-4 w-4" />
              Nova Conta Cadastrada
            </Button>
          )
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Select value={buildingFilter} onValueChange={setBuildingFilter}>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="Prédio" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos os prédios</SelectItem>
            {buildings?.map((building) =>
              building.id === undefined ? null : (
                <SelectItem key={building.id} value={String(building.id)}>
                  {building.name}
                </SelectItem>
              )
            )}
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos os tipos</SelectItem>
            {billingAccountTypeValues.map((type) => (
              <SelectItem key={type} value={type}>
                {ACCOUNT_TYPE_LABELS[type]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {!isLoading && (accounts?.length ?? 0) === 0 ? (
        <p className="rounded-md border-2 border-dashed py-12 text-center text-sm text-muted-foreground">
          Nenhuma conta cadastrada
        </p>
      ) : (
        <DataTable<BillingAccount>
          columns={columns}
          dataSource={accounts}
          loading={isLoading}
          rowKey="id"
        />
      )}

      <AccountFormModal
        open={crud.isModalOpen}
        account={crud.editingItem}
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
