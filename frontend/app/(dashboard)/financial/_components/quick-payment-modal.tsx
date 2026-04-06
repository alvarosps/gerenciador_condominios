'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export function QuickPaymentModal({
  open,
  onClose,
  personId,
  personName,
  year,
  month,
}: {
  open: boolean;
  onClose: () => void;
  personId: number;
  personName: string;
  year: number;
  month: number;
}) {
  const [amount, setAmount] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const queryClient = useQueryClient();

  const referenceMonth = `${year}-${String(month).padStart(2, '0')}-01`;

  const handleSave = async () => {
    const value = parseFloat(amount);
    if (isNaN(value) || value <= 0) {
      toast.error('Informe um valor válido');
      return;
    }

    setIsSaving(true);
    try {
      await apiClient.post('/person-payments/', {
        person_id: personId,
        reference_month: referenceMonth,
        amount: value,
        payment_date: new Date().toISOString().split('T')[0],
      });
      toast.success(`Pagamento de R$ ${value.toFixed(2)} registrado para ${personName}`);
      await queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      await queryClient.invalidateQueries({ queryKey: ['person-payments'] });
      await queryClient.invalidateQueries({ queryKey: ['expenses'] });
      setAmount('');
      onClose();
    } catch {
      toast.error('Erro ao registrar pagamento');
    } finally {
      setIsSaving(false);
    }
  };

  const handleClose = () => {
    setAmount('');
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) handleClose(); }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Registrar Pagamento — {personName}</DialogTitle>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div>
            <Label>Valor do Pagamento</Label>
            <div className="relative mt-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                R$
              </span>
              <Input
                type="number"
                min={0.01}
                step="0.01"
                placeholder="0,00"
                className="pl-10"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                autoFocus
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isSaving}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Registrando...
              </>
            ) : (
              'Registrar'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
