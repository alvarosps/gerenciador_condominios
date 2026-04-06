'use client';

import { useState } from 'react';
import { AlertTriangle, Loader2, Rocket } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { MonthStatus } from '@/lib/api/hooks/use-month-advance';
import { formatMonthYear } from '@/lib/utils/formatters';

interface AdvanceDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (force: boolean, notes: string) => void;
  year: number;
  month: number;
  status: MonthStatus | undefined;
  isPending: boolean;
}

export function AdvanceDialog({
  open,
  onClose,
  onConfirm,
  year,
  month,
  status,
  isPending,
}: AdvanceDialogProps) {
  const [force, setForce] = useState(false);
  const [notes, setNotes] = useState('');

  const monthLabel = formatMonthYear(year, month);
  const hasWarnings = status?.validation.has_warnings ?? false;
  const warningCount = status?.validation.warning_count ?? 0;

  const handleConfirm = () => {
    onConfirm(force, notes);
  };

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) {
      setForce(false);
      setNotes('');
      onClose();
    }
  };

  const canConfirm = !hasWarnings || force;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Rocket className="h-5 w-5 text-success" />
            Finalizar {monthLabel}
          </DialogTitle>
          <DialogDescription>
            Esta ação irá criar um snapshot financeiro do mês e preparar o próximo mês
            automaticamente.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {hasWarnings && (
            <div className="rounded-md border border-warning/30 bg-warning/5 p-3 space-y-1">
              <div className="flex items-center gap-2 text-warning">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                <span className="text-sm font-medium">
                  {warningCount} pendência{warningCount !== 1 ? 's' : ''} encontrada
                  {warningCount !== 1 ? 's' : ''}
                </span>
              </div>
              <p className="text-xs text-muted-foreground ml-6">
                Revise o checklist antes de prosseguir. Você pode forçar o avanço marcando a opção
                abaixo.
              </p>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="notes">Observações (opcional)</Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Ex: Água da kitnet 207 chegará amanhã..."
              rows={3}
            />
          </div>

          {hasWarnings && (
            <div className="flex items-center gap-2">
              <Checkbox
                id="force"
                checked={force}
                onCheckedChange={(checked) => setForce(checked === true)}
              />
              <Label htmlFor="force" className="text-sm cursor-pointer">
                Forçar finalização mesmo com pendências
              </Label>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isPending}>
            Cancelar
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={isPending || !canConfirm}
            className="bg-success hover:bg-success/90"
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Finalizando...
              </>
            ) : (
              <>
                <Rocket className="h-4 w-4 mr-2" />
                Finalizar Mês
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
