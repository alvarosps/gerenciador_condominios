'use client';

import { AlertTriangle, Info } from 'lucide-react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useApplyInvoice } from '@/lib/api/hooks/use-bills';
import { showFinanceMutationError } from '@/lib/utils/error-handler';
import { competenceMonthLabel, dueDateLabel, formatCurrency } from '@/lib/utils/formatters';
import { ROUTES } from '@/lib/utils/constants';
import type { Bill } from '@/lib/schemas/finances/bill.schema';
import type { ParsedInvoice } from '@/lib/schemas/finances/invoice-parse.schema';

interface ApplyInvoiceDialogProps {
  open: boolean;
  bill: Bill;
  draft: ParsedInvoice;
  file: File;
  onClose: () => void;
}

/** Sum of the draft's line amounts — display-only preview total (never re-derives money for the
 *  actual write, which the backend recomputes atomically from the re-parsed PDF, S69). */
function draftTotal(draft: ParsedInvoice): number {
  return draft.line_items.reduce((sum, line) => sum + line.amount, 0);
}

/**
 * Preview + confirmation step of "Importar fatura" on the row (S75, 2nd of 2 steps): the caller
 * already parsed the PDF via `useParseInvoice` (step 1, the ONLY surface that carries `warnings` —
 * `apply_invoice`'s 200 response never does, S69 verified). Divergent matched account blocks
 * confirmation client-side (mirrors the backend's 400).
 */
export function ApplyInvoiceDialog({ open, bill, draft, file, onClose }: ApplyInvoiceDialogProps) {
  const applyInvoice = useApplyInvoice();
  const router = useRouter();

  const billAccountId = bill.billing_account_id ?? bill.billing_account?.id ?? null;
  const accountDiverges = draft.matched_account?.id !== billAccountId;

  function handleConfirm() {
    if (bill.id === undefined || accountDiverges) return;
    applyInvoice.mutate(
      { bill_id: bill.id, file },
      {
        onSuccess: () => {
          toast.success('Fatura aplicada');
          onClose();
        },
        onError: (error) => {
          showFinanceMutationError(error, 'Erro ao aplicar fatura', () =>
            router.push(ROUTES.FINANCES_MONTH_CLOSE)
          );
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Importar fatura — {bill.description}</DialogTitle>
          <DialogDescription>
            Revise os dados extraídos antes de aplicar a fatura nesta conta.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Conta casada</span>
            <span>{draft.matched_account?.name ?? 'Nenhuma'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Competência</span>
            <span>{competenceMonthLabel(draft.bill.competence_month)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Vencimento</span>
            <span>{dueDateLabel(draft.bill.due_date)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Total do draft</span>
            <span className="font-medium tabular-nums">{formatCurrency(draftTotal(draft))}</span>
          </div>
        </div>

        {accountDiverges && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Conta divergente: a fatura lida não corresponde à conta desta cobrança. Não é possível
              aplicar.
            </AlertDescription>
          </Alert>
        )}

        {draft.warnings.length > 0 && (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <ul className="list-disc space-y-1 pl-4">
                {draft.warnings.map((warning, index) => (
                  <li key={`${String(index)}-${warning}`}>{warning}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={accountDiverges || applyInvoice.isPending}
          >
            {applyInvoice.isPending ? 'Aplicando...' : 'Confirmar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
