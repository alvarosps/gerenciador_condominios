'use client';

import { useRef, useState } from 'react';
import { CalendarPlus, ChevronLeft, ChevronRight, FileUp, Plus, ShoppingBag } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
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
import { PageHeader } from '@/components/layouts/page-header';
import { useDeleteBill, useGenerateMonthBills, useParseInvoice } from '@/lib/api/hooks/use-bills';
import { useMonthBoard } from '@/lib/api/hooks/use-month-board';
import { useAuthStore } from '@/store/auth-store';
import { handleError } from '@/lib/utils/error-handler';
import { formatCurrency, formatMonthYear } from '@/lib/utils/formatters';
import { useCrudPage } from '@/lib/hooks/use-crud-page';
import type { Bill } from '@/lib/schemas/finances/bill.schema';
import type { BillLifecycleState } from '@/lib/schemas/finances/category.schema';
import type { ParsedInvoice } from '@/lib/schemas/finances/invoice-parse.schema';
import { IptuRiskBanner } from '../_components/iptu-risk-banner';
import { ConsolidateDebtDialog } from '../accounts/[id]/_components/consolidate-debt-dialog';
import { ApplyInvoiceDialog } from './_components/apply-invoice-dialog';
import { buildBillColumns } from './_components/bill-columns';
import { BillFormModal } from './_components/bill-form-modal';
import { BillPaymentDialog } from './_components/bill-payment-dialog';
import { GenerateMissingBanner } from './_components/generate-missing-banner';
import { OverdueSection, toConsolidableBills } from './_components/overdue-section';
import { QuickBillDialog } from './_components/quick-bill-dialog';
import { ThirdPartyPurchaseDialog } from './_components/third-party-purchase-dialog';

const ALL = 'all';

const LIFECYCLE_OPTIONS: { value: BillLifecycleState; label: string }[] = [
  { value: 'active', label: 'Ativas' },
  { value: 'suspended', label: 'Suspensas' },
  { value: 'deferred', label: 'Adiadas' },
];

type LifecycleFilter = typeof ALL | BillLifecycleState;

const LIFECYCLE_FILTER_VALUES: ReadonlySet<string> = new Set([
  ALL,
  ...LIFECYCLE_OPTIONS.map((option) => option.value),
]);

function isLifecycleFilter(value: string): value is LifecycleFilter {
  return LIFECYCLE_FILTER_VALUES.has(value);
}

/** Applies the situação filter to a bill list — client-side, over the board's own sections. */
function filterByLifecycle(bills: Bill[], lifecycleFilter: LifecycleFilter): Bill[] {
  if (lifecycleFilter === ALL) return bills;
  return bills.filter((bill) => bill.lifecycle_state === lifecycleFilter);
}

export default function BillsPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const now = new Date();
  const [period, setPeriod] = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });
  const [lifecycleFilter, setLifecycleFilter] = useState<LifecycleFilter>(ALL);
  const [payingBill, setPayingBill] = useState<Bill | null>(null);
  const [importDraft, setImportDraft] = useState<ParsedInvoice | null>(null);
  const [quickBillOpen, setQuickBillOpen] = useState(false);
  const [purchaseOpen, setPurchaseOpen] = useState(false);
  const [rowImportBill, setRowImportBill] = useState<Bill | null>(null);
  const [rowImport, setRowImport] = useState<{
    bill: Bill;
    file: File;
    draft: ParsedInvoice;
  } | null>(null);
  const [consolidatingAccount, setConsolidatingAccount] = useState<{
    accountId: number;
    accountType: NonNullable<Bill['billing_account']>['account_type'];
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const rowFileInputRef = useRef<HTMLInputElement>(null);
  const parseInvoice = useParseInvoice();
  // Second parse_invoice instance for the row "Importar fatura" flow (step 1 of 2, S75) — kept
  // separate from the header's `parseInvoice` above so the two entry points never race each other.
  const rowParseInvoice = useParseInvoice();
  // Always-available generation path (header action) — shares this mutation's success/error
  // toast handling (baked into the hook itself, use-bills.ts) with the contextual
  // GenerateMissingBanner shortcut below, so neither call site duplicates the PT toast logic.
  const generateMonth = useGenerateMonthBills();

  function shiftMonth(delta: number) {
    const base = new Date(period.year, period.month - 1 + delta, 1);
    setPeriod({ year: base.getFullYear(), month: base.getMonth() + 1 });
  }

  function handleLifecycleFilterChange(value: string) {
    if (isLifecycleFilter(value)) setLifecycleFilter(value);
  }

  function handleGenerateMonth() {
    generateMonth.mutate({ year: period.year, month: period.month });
  }

  // Single data source (S74): the board already carries the fixed Atrasadas/deferred-suspended
  // sections plus the per-building groups of the selected competence, so the page no longer pulls
  // the full bills list nor re-groups/re-sorts/re-sums client-side.
  const { data: board, isLoading } = useMonthBoard(period.year, period.month);

  const overdue = filterByLifecycle(board?.overdue ?? [], lifecycleFilter);
  const deferredSuspended = filterByLifecycle(board?.deferred_suspended ?? [], lifecycleFilter);
  const groups = (board?.groups ?? []).map((group) => ({
    ...group,
    bills: filterByLifecycle(group.bills, lifecycleFilter),
  }));

  const deleteMutation = useDeleteBill();

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
    onImportInvoice: (bill) => {
      setRowImportBill(bill);
      rowFileInputRef.current?.click();
    },
  });

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

  /**
   * Row "Importar fatura" — step 1 of 2 (S75): parses the PDF to a DRAFT (never writes) so the
   * `ApplyInvoiceDialog` can surface its `warnings` BEFORE the user confirms `apply_invoice`
   * (the apply endpoint's 200 response never carries warnings, S69 verified).
   */
  function handleRowInvoiceSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    const bill = rowImportBill;
    setRowImportBill(null);
    if (!file || !bill) return;
    rowParseInvoice.mutate(file, {
      onSuccess: (draft) => {
        setRowImport({ bill, file, draft });
      },
      onError: (error) => {
        handleError(error, 'Não foi possível ler a fatura');
        toast.error('Não foi possível ler a fatura. Verifique o PDF.');
      },
    });
  }

  function closeRowImport() {
    setRowImport(null);
  }

  function handleConsolidate(bill: Bill) {
    const accountId = bill.billing_account?.id;
    const accountType = bill.billing_account?.account_type;
    if (accountId === undefined || accountType === undefined) return;
    setConsolidatingAccount({ accountId, accountType });
  }

  const isEmpty =
    !isLoading &&
    overdue.length === 0 &&
    deferredSuspended.length === 0 &&
    groups.every((group) => group.bills.length === 0);

  return (
    <div>
      <PageHeader
        title="Contas do Condomínio"
        description="Gerencie as contas a pagar do condomínio"
        actions={
          isAdmin && (
            <>
              <Button
                variant="outline"
                onClick={handleGenerateMonth}
                disabled={generateMonth.isPending}
              >
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
              <Button variant="outline" onClick={() => setQuickBillOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Conta avulsa
              </Button>
              <Button variant="outline" onClick={() => setPurchaseOpen(true)}>
                <ShoppingBag className="mr-2 h-4 w-4" />
                Nova compra de terceiro
              </Button>
              <Button onClick={crud.openCreateModal}>
                <Plus className="mr-2 h-4 w-4" />
                Nova Conta
              </Button>
            </>
          )
        }
      />

      {isAdmin && (
        <div className="mb-4">
          <IptuRiskBanner />
        </div>
      )}

      {isAdmin && board && (
        <GenerateMissingBanner
          missingCount={board.generation.missing_count}
          year={period.year}
          month={period.month}
        />
      )}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            onClick={() => shiftMonth(-1)}
            aria-label="Mês anterior"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="min-w-[10rem] text-center text-sm font-medium">
            {formatMonthYear(period.year, period.month)}
          </span>
          <Button
            variant="outline"
            size="icon"
            onClick={() => shiftMonth(1)}
            aria-label="Próximo mês"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        <Select value={lifecycleFilter} onValueChange={handleLifecycleFilterChange}>
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

      {board && (
        <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-1 text-sm">
          <span>
            A pagar <span className="font-medium">{formatCurrency(board.totals.due)}</span>
          </span>
          <span>
            Pago <span className="font-medium">{formatCurrency(board.totals.paid)}</span>
          </span>
          <span>
            Restante <span className="font-medium">{formatCurrency(board.totals.remaining)}</span>
          </span>
          <span>
            Atrasado <span className="font-medium">{formatCurrency(board.totals.overdue)}</span>
          </span>
        </div>
      )}

      <OverdueSection
        overdue={overdue}
        deferredSuspended={deferredSuspended}
        columns={columns}
        overdueTotal={board?.totals.overdue ?? '0.00'}
        onConsolidate={handleConsolidate}
      />

      {isEmpty ? (
        <p className="rounded-md border-2 border-dashed py-12 text-center text-sm text-muted-foreground">
          Nenhuma conta cadastrada
        </p>
      ) : (
        <Accordion
          // Re-key on the group set so the default-open state re-applies once bills load.
          key={groups.map((group) => group.building_id ?? 'condominio').join(',')}
          type="multiple"
          defaultValue={groups.map((group) => String(group.building_id ?? 'condominio'))}
          className="space-y-4"
        >
          {groups.map((group) => (
            <AccordionItem
              key={group.building_id ?? 'condominio'}
              value={String(group.building_id ?? 'condominio')}
            >
              <AccordionTrigger className="px-4">
                <div className="flex items-center gap-2">
                  <span>{group.building_label}</span>
                  <Badge variant="secondary">{group.bills.length} contas</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4">
                <DataTable<Bill>
                  columns={columns}
                  dataSource={group.bills}
                  loading={isLoading}
                  rowKey="id"
                  pagination={false}
                />
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
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

      <QuickBillDialog
        open={quickBillOpen}
        onClose={() => setQuickBillOpen(false)}
        year={period.year}
        month={period.month}
      />

      {isAdmin && (
        <ThirdPartyPurchaseDialog
          open={purchaseOpen}
          onClose={() => setPurchaseOpen(false)}
          year={period.year}
          month={period.month}
        />
      )}

      <input
        ref={rowFileInputRef}
        type="file"
        accept="application/pdf"
        hidden
        onChange={handleRowInvoiceSelected}
      />

      {rowImport && (
        <ApplyInvoiceDialog
          open
          bill={rowImport.bill}
          draft={rowImport.draft}
          file={rowImport.file}
          onClose={closeRowImport}
        />
      )}

      {consolidatingAccount && board && (
        <ConsolidateDebtDialog
          open
          onClose={() => setConsolidatingAccount(null)}
          accountId={consolidatingAccount.accountId}
          accountType={consolidatingAccount.accountType}
          bills={toConsolidableBills(board, consolidatingAccount.accountId)}
        />
      )}

      <AlertDialog open={crud.deleteDialogOpen} onOpenChange={crud.setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir conta</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir{' '}
              {crud.itemToDelete?.description ? `"${crud.itemToDelete.description}"` : 'esta conta'}
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
