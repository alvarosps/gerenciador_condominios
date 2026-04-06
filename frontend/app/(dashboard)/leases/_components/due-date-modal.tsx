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
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent } from '@/components/ui/card';
import { Calendar, AlertTriangle, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { useChangeDueDate } from '@/lib/api/hooks/use-leases';
import { type Lease } from '@/lib/schemas/lease.schema';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';

interface Props {
  open: boolean;
  lease: Lease | null;
  onClose: () => void;
}

interface ChangeDueDateResult {
  old_due_day: number;
  new_due_day: number;
  old_due_date: string;
  new_due_date: string;
  change_fee: number;
  days_difference: number;
  daily_rate: number;
  total_due: number;
  message: string;
}

export function DueDateModal({ open, lease, onClose }: Props) {
  const changeMutation = useChangeDueDate();
  const [newDueDay, setNewDueDay] = useState<number | null>(null);
  const [result, setResult] = useState<ChangeDueDateResult | null>(null);

  const handleChange = async () => {
    if (!lease?.id || !newDueDay) {
      toast.error('Por favor, informe o novo dia de vencimento');
      return;
    }

    if (newDueDay === lease.responsible_tenant?.due_day) {
      toast.warning('O novo dia é igual ao dia atual');
      return;
    }

    try {
      const data = await changeMutation.mutateAsync({
        leaseId: lease.id,
        new_due_day: newDueDay,
      });
      setResult(data);
      toast.success(data.message || 'Data de vencimento alterada com sucesso!');
    } catch (error) {
      toast.error('Erro ao alterar data de vencimento');
      console.error('Due date change error:', error);
    }
  };

  const handleClose = () => {
    setNewDueDay(null);
    setResult(null);
    onClose();
  };

  if (!lease) return null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Alterar Data de Vencimento</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <Alert className="border-warning/20 bg-warning/10">
            <AlertTriangle className="h-4 w-4 text-warning" />
            <AlertDescription className="ml-2">
              <p className="font-medium text-warning">Taxa de Alteração de Vencimento</p>
              <p className="text-sm text-warning">
                A alteração da data de vencimento tem uma taxa calculada com base no valor diário do aluguel multiplicado pela diferença de dias.
              </p>
            </AlertDescription>
          </Alert>

          <Card>
            <CardContent className="pt-6">
              <dl className="space-y-3">
                <div className="flex justify-between py-2 border-b">
                  <dt className="font-medium text-sm text-muted-foreground">Apartamento</dt>
                  <dd className="text-sm text-foreground">
                    {lease.apartment?.building?.name} - Apto {lease.apartment?.number}
                  </dd>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <dt className="font-medium text-sm text-muted-foreground">Inquilino</dt>
                  <dd className="text-sm text-foreground">
                    {lease.responsible_tenant?.name}
                  </dd>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <dt className="font-medium text-sm text-muted-foreground">Valor do Aluguel</dt>
                  <dd className="text-sm text-foreground">
                    {formatCurrency(lease.apartment?.rental_value ?? 0)}
                  </dd>
                </div>
                <div className="flex justify-between py-2">
                  <dt className="font-medium text-sm text-muted-foreground">Vencimento Atual</dt>
                  <dd className="text-sm font-bold text-foreground">
                    Dia {lease.responsible_tenant?.due_day ?? '-'}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {!result && (
            <div className="space-y-2">
              <label className="block text-sm font-medium">
                Novo Dia de Vencimento (1-31)
              </label>
              <Input
                type="number"
                value={newDueDay ?? ''}
                onChange={(e) => setNewDueDay(Number(e.target.value))}
                min={1}
                max={31}
                placeholder="Ex: 15"
              />
              <p className="text-xs text-muted-foreground">
                Informe o novo dia do mês para vencimento do aluguel
              </p>
            </div>
          )}

          {result && (
            <Card className="border-info/20 bg-info/10">
              <CardContent className="pt-6">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Vencimento Anterior:</span>
                    <span className="text-lg font-medium">
                      Dia {result.old_due_day} ({formatDate(result.old_due_date)})
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Novo Vencimento:</span>
                    <span className="text-lg font-bold text-info">
                      Dia {result.new_due_day} ({formatDate(result.new_due_date)})
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Diferença de Dias:</span>
                    <span className="text-lg font-medium">
                      {result.days_difference} dias
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Taxa Diária:</span>
                    <span className="text-lg font-medium">
                      {formatCurrency(result.daily_rate)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center pt-3 border-t">
                    <span className="text-muted-foreground">Taxa de Alteração:</span>
                    <span className="text-lg font-medium">
                      {formatCurrency(result.change_fee)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center pt-3 border-t-2 border-info/30">
                    <span className="text-foreground font-medium">Total a Pagar:</span>
                    <span className="text-2xl font-bold text-info">
                      {formatCurrency(result.total_due)}
                    </span>
                  </div>
                  {result.message && (
                    <Alert className="mt-3 border-success/20 bg-success/10">
                      <CheckCircle className="h-4 w-4 text-success" />
                      <AlertDescription className="ml-2 text-sm text-success">
                        {result.message}
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Fechar
          </Button>
          {!result && (
            <Button
              onClick={handleChange}
              disabled={changeMutation.isPending}
            >
              <Calendar className="h-4 w-4 mr-2" />
              Alterar Vencimento
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
