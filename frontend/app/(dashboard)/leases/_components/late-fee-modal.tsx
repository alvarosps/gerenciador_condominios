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
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent } from '@/components/ui/card';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { CalendarIcon, Calculator, Info, AlertTriangle, CheckCircle } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { useCalculateLateFee } from '@/lib/api/hooks/use-leases';
import { Lease } from '@/lib/schemas/lease.schema';
import { formatCurrency } from '@/lib/utils/formatters';

interface Props {
  open: boolean;
  lease: Lease | null;
  onClose: () => void;
}

interface LateFeeResult {
  late_fee: number;
  days_late: number;
  daily_rate: number;
  message: string;
}

export function LateFeeModal({ open, lease, onClose }: Props) {
  const calculateMutation = useCalculateLateFee();
  const [paymentDate, setPaymentDate] = useState<Date>(new Date());
  const [result, setResult] = useState<LateFeeResult | null>(null);

  const handleCalculate = async () => {
    if (!lease?.id || !paymentDate) return;

    try {
      const data = await calculateMutation.mutateAsync({
        leaseId: lease.id,
        payment_date: format(paymentDate, 'yyyy-MM-dd'),
      });
      setResult(data);
      toast.success('Multa calculada com sucesso!');
    } catch (error) {
      toast.error('Erro ao calcular multa');
      console.error('Late fee calculation error:', error);
    }
  };

  const handleClose = () => {
    setPaymentDate(new Date());
    setResult(null);
    onClose();
  };

  if (!lease) return null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Calcular Multa por Atraso</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription className="ml-2">
              <p className="font-medium">Calcule a multa por atraso no pagamento</p>
              <p className="text-sm text-muted-foreground">
                Informe a data de pagamento para calcular a multa baseada em 5% ao dia sobre o valor diário do aluguel.
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
                  <dt className="font-medium text-sm text-gray-600">Dia de Vencimento</dt>
                  <dd className="text-sm text-gray-900">
                    Dia {lease.due_day}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <div className="space-y-2">
            <label className="block text-sm font-medium">
              Data de Pagamento
            </label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    'w-full pl-3 text-left font-normal',
                    !paymentDate && 'text-muted-foreground'
                  )}
                >
                  {paymentDate ? (
                    format(paymentDate, 'dd/MM/yyyy', { locale: ptBR })
                  ) : (
                    <span>Selecione a data de pagamento</span>
                  )}
                  <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={paymentDate}
                  onSelect={(date) => date && setPaymentDate(date)}
                  locale={ptBR}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>

          {result && (
            <Card className={cn(
              result.days_late > 0
                ? 'border-orange-200 bg-orange-50'
                : 'border-green-200 bg-green-50'
            )}>
              <CardContent className="pt-6">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Dias de Atraso:</span>
                    <span className={cn(
                      'text-lg font-bold',
                      result.days_late > 0 ? 'text-red-600' : 'text-green-600'
                    )}>
                      {result.days_late} dias
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Taxa Diária:</span>
                    <span className="text-lg font-medium">
                      {formatCurrency(result.daily_rate)}
                    </span>
                  </div>
                  <div className={cn(
                    'flex justify-between items-center pt-3 border-t-2',
                    result.days_late > 0 ? 'border-orange-300' : 'border-green-300'
                  )}>
                    <span className="text-gray-900 font-medium">Multa Total:</span>
                    <span className={cn(
                      'text-2xl font-bold',
                      result.days_late > 0 ? 'text-red-600' : 'text-green-600'
                    )}>
                      {formatCurrency(result.late_fee)}
                    </span>
                  </div>
                  {result.message && (
                    <Alert className={cn(
                      'mt-3',
                      result.days_late > 0
                        ? 'border-yellow-200 bg-yellow-50'
                        : 'border-green-200 bg-green-50'
                    )}>
                      {result.days_late > 0 ? (
                        <AlertTriangle className="h-4 w-4 text-yellow-600" />
                      ) : (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      )}
                      <AlertDescription className={cn(
                        'ml-2 text-sm',
                        result.days_late > 0 ? 'text-yellow-800' : 'text-green-800'
                      )}>
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
          <Button
            onClick={handleCalculate}
            disabled={calculateMutation.isPending}
          >
            <Calculator className="h-4 w-4 mr-2" />
            Calcular Multa
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
