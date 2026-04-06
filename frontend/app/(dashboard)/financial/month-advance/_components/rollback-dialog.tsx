'use client';

import { useState } from 'react';
import { AlertTriangle, Loader2, RotateCcw } from 'lucide-react';
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
import { formatMonthYear } from '@/lib/utils/formatters';

interface RollbackDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  year: number;
  month: number;
  isPending: boolean;
}

export function RollbackDialog({
  open,
  onClose,
  onConfirm,
  year,
  month,
  isPending,
}: RollbackDialogProps) {
  const [confirmed, setConfirmed] = useState(false);

  const monthLabel = formatMonthYear(year, month);

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) {
      setConfirmed(false);
      onClose();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <RotateCcw className="h-5 w-5" />
            Reverter {monthLabel}
          </DialogTitle>
          <DialogDescription>
            Esta ação irá desfazer o fechamento do mês, excluindo o snapshot e os registros criados
            automaticamente para o próximo mês.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 space-y-1">
            <div className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              <span className="text-sm font-medium">Atenção: ação irreversível</span>
            </div>
            <ul className="text-xs text-muted-foreground ml-6 space-y-0.5 list-disc">
              <li>O snapshot financeiro do mês será excluído</li>
              <li>Pagamentos de funcionários criados automaticamente serão excluídos</li>
              <li>Agendamentos de pagamento criados automaticamente serão excluídos</li>
              <li>Dados registrados manualmente não serão afetados</li>
            </ul>
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="confirm-rollback"
              checked={confirmed}
              onCheckedChange={(checked) => setConfirmed(checked === true)}
            />
            <Label htmlFor="confirm-rollback" className="text-sm cursor-pointer">
              Entendo as consequências e confirmo a reversão
            </Label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isPending}>
            Cancelar
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isPending || !confirmed}
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Revertendo...
              </>
            ) : (
              <>
                <RotateCcw className="h-4 w-4 mr-2" />
                Reverter Mês
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
