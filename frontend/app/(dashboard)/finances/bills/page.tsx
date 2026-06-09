'use client';

import { useRef, useState } from 'react';
import { CalendarPlus, FileUp, Plus } from 'lucide-react';
import { toast } from 'sonner';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DataTable } from '@/components/tables/data-table';
import {
  useBills,
  useDeleteBill,
  useGenerateMonthBills,
  useParseInvoice,
} from '@/lib/api/hooks/use-bills';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useAuthStore } from '@/store/auth-store';
import { handleError } from '@/lib/utils/error-handler';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import type { Bill } from '@/lib/schemas/finances/bill.schema';
import type { BillFilters } from '@/lib/api/hooks/use-bills';
import type { ParsedInvoice } from '@/lib/schemas/finances/invoice-parse.schema';
import { IptuRiskBanner } from '../_components/iptu-risk-banner';
import { buildBillColumns } from './_components/bill-columns';
import { BillFormModal } from './_components/bill-form-modal';
import { BillPaymentDialog } from './_components/bill-payment-dialog';

const ALL = 'all';

const LIFECYCLE_OPTIONS = [
  { value: 'active', label: 'Ativas' },
  { value: 'suspended', label: 'Suspensas' },
  { value: 'deferred', label: 'Adiadas' },
  { value: 'canceled', label: 'Canceladas' },
] as const;

export default function BillsPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const now = new Date();
  const [period] = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });
  const [buildingFilter, setBuildingFilter] = useState<string>(ALL);
  const [lifecycleFilter, setLifecycleFilter] = useState<string>(ALL);
  const [payingBill, setPayingBill] = useState<Bill | null>(null);
  const [importDraft, setImportDraft] = useState<ParsedInvoice | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const parseInvoice = useParseInvoice();

  const filters: BillFilters = {
    ...(buildingFilter === ALL ? {} : { building_id: Number(buildingFilter) }),
    ...(lifecycleFilter === ALL ? {} : { lifecycle_state: lifecycleFilter }),
  };

  const { data: bills, isLoading } = useBills(filters);
  const { data: buildings } = useBuildings();
  const deleteMutation = useDeleteBill();
  const generateMonth = useGenerateMonthBills();

  const crud = useCrudPage<Bill>({
    entityName: 'conta',
    entityNamePlural: 'contas',
    deleteMutation,
    deleteErrorMessage: 'Erro ao excluir conta.',
  });

  const columns = buildBillColumns({
    isAdmin,
    onEdit: (bill) => crud.openEditModal(bill),
    onPay: (bill) => {
      setPayingBill(bill);
    },
    onDelete: (bill) => {
      crud.setItemToDelete(bill);
      if (bill.id !== undefined) crud.handleDeleteClick(bill.id);
    },
  });

  function handleGenerateMonth() {
    generateMonth.mutate(
      { year: period.year, month: period.month },
      {
        onSuccess: (result) => {
          toast.success(`${String(result.created)} conta(s) gerada(s)`);
        },
        onError: (error) => {
          handleError(error, 'Erro ao gerar contas do mês');
        },
      },
    );
  }

  function handleInvoiceSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // Reset the input so re-selecting the same file fires change again. The PDF is sent and
    // discarded by the backend — the frontend never persists it (design #4).
    event.target.value = '';
    if (!file) return;
    parseInvoice.mutate(file, {
      onSuccess: (draft) => {
        setImportDraft(draft);
      },
      onError: (error) => {
        handleError(error, 'Não foi possível ler a fatura');
        toast.error('Não foi possível ler a fatura. Verifique o PDF.');
      },
    });
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Contas do Condomínio</h1>
          <p className="mt-1 text-muted-foreground">Gerencie as contas a pagar do condomínio</p>
        </div>
        {isAdmin && (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={handleGenerateMonth} disabled={generateMonth.isPending}>
              <CalendarPlus className="mr-2 h-4 w-4" />
              Gerar contas do mês
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              hidden
              onChange={handleInvoiceSelected}
            />
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={parseInvoice.isPending}
            >
              <FileUp className="mr-2 h-4 w-4" />
              {parseInvoice.isPending ? 'Lendo fatura...' : 'Importar fatura (PDF)'}
            </Button>
            <Button onClick={crud.openCreateModal}>
              <Plus className="mr-2 h-4 w-4" />
              Nova Conta
            </Button>
          </div>
        )}
      </div>

      {isAdmin && (
        <div className="mb-4">
          <IptuRiskBanner />
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Select value={buildingFilter} onValueChange={setBuildingFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Prédio" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos os prédios</SelectItem>
            {buildings?.map((building) =>
              building.id === undefined ? null : (
                <SelectItem key={building.id} value={String(building.id)}>
                  {building.name}
                </SelectItem>
              ),
            )}
          </SelectContent>
        </Select>

        <Select value={lifecycleFilter} onValueChange={setLifecycleFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Situação" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todas as situações</SelectItem>
            {LIFECYCLE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {!isLoading && (bills?.length ?? 0) === 0 ? (
        <p className="rounded-md border-2 border-dashed py-12 text-center text-sm text-muted-foreground">
          Nenhuma conta cadastrada
        </p>
      ) : (
        <DataTable<Bill>
          columns={columns}
          dataSource={bills}
          loading={isLoading}
          rowKey="id"
        />
      )}

      <BillFormModal open={crud.isModalOpen} bill={crud.editingItem} onClose={crud.closeModal} />

      <BillFormModal
        open={importDraft !== null}
        draft={importDraft}
        onClose={() => {
          setImportDraft(null);
        }}
      />

      <BillPaymentDialog
        open={payingBill !== null}
        billId={payingBill?.id ?? null}
        amountRemaining={payingBill?.amount_remaining}
        description={payingBill?.description}
        onClose={() => {
          setPayingBill(null);
        }}
      />

      <AlertDialog open={crud.deleteDialogOpen} onOpenChange={crud.setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir conta</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir{' '}
              {crud.itemToDelete?.description
                ? `"${crud.itemToDelete.description}"`
                : 'esta conta'}
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
