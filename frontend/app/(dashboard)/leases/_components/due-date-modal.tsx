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
import { Lease } from '@/lib/schemas/lease.schema';
import { formatCurrency } from '@/lib/utils/formatters';

interface Props {
  open: boolean;
  lease: Lease | null;
  onClose: () => void;
}

interface ChangeDueDateResult {
  old_due_day: number;
  new_due_day: number;
  change_fee: number;
  days_difference: number;
  daily_rate: number;
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

    if (newDueDay === lease.due_day) {
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
          <Alert className="border-yellow-200 bg-yellow-50">
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
            <AlertDescription className="ml-2">
              <p className="font-medium text-yellow-900">Taxa de Alteração de Vencimento</p>
              <p className="text-sm text-yellow-800">
                A alteração da data de vencimento tem uma taxa calculada com base no valor diário do aluguel multiplicado pela diferença de dias.
              </p>
            </AlertDescription>
          </Alert>

          <Card>
            <CardContent className="pt-6">
              <dl className="space-y-3">
                <div className="flex justify-between py-2 border-b">
                  <dt className="font-medium text-sm text-gray-600">Apartamento</dt>
                  <dd className="text-sm text-gray-900">
                    {lease.apartment?.building?.name} - Apto {lease.apartment?.number}
                  </dd>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <dt className="font-medium text-sm text-gray-600">Inquilino</dt>
                  <dd className="text-sm text-gray-900">
                    {lease.responsible_tenant?.name}
                  </dd>
                </div>
                <div className="flex justify-between py-2 border-b">
                  <dt className="font-medium text-sm text-gray-600">Valor do Aluguel</dt>
                  <dd className="text-sm text-gray-900">
                    {formatCurrency(lease.rental_value)}
                  </dd>
                </div>
                <div className="flex justify-between py-2">
                  <dt className="font-medium text-sm text-gray-600">Vencimento Atual</dt>
                  <dd className="text-sm font-bold text-gray-900">
                    Dia {lease.due_day}
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
            <Card className="border-blue-200 bg-blue-50">
              <CardContent className="pt-6">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Vencimento Anterior:</span>
                    <span className="text-lg font-medium">
                      Dia {result.old_due_day}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Novo Vencimento:</span>
                    <span className="text-lg font-bold text-blue-600">
                      Dia {result.new_due_day}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Diferença de Dias:</span>
                    <span className="text-lg font-medium">
                      {result.days_difference} dias
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Taxa Diária:</span>
                    <span className="text-lg font-medium">
                      {formatCurrency(result.daily_rate)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center pt-3 border-t-2 border-blue-300">
                    <span className="text-gray-900 font-medium">Taxa de Alteração:</span>
                    <span className="text-2xl font-bold text-blue-600">
                      {formatCurrency(result.change_fee)}
                    </span>
                  </div>
                  {result.message && (
                    <Alert className="mt-3 border-green-200 bg-green-50">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      <AlertDescription className="ml-2 text-sm text-green-800">
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
