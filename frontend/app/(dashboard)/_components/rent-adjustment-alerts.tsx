'use client';

import { useState } from 'react';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { TrendingUp, CheckCircle2, ArrowRight, CalendarDays, Info } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  useRentAdjustmentAlerts,
  useApplyRentAdjustment,
} from '@/lib/api/hooks/use-rent-adjustments';
import { formatCurrency } from '@/lib/utils/formatters';
import { handleError } from '@/lib/utils/error-handler';
import type { RentAdjustmentAlert } from '@/lib/schemas/rent-adjustment.schema';
import { toast } from 'sonner';

function StatusBadge({ alert }: { alert: RentAdjustmentAlert }) {
  if (alert.status === 'overdue') {
    return (
      <Badge variant="destructive">Atrasado {Math.abs(alert.days_until)} dias</Badge>
    );
  }
  return (
    <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">
      Em {alert.days_until} dias
    </Badge>
  );
}

function formatDateBR(dateStr: string): string {
  return format(parseISO(dateStr), 'dd/MM/yyyy', { locale: ptBR });
}

function IpcaSourceBadge({ source }: { source: 'ipca' | 'fallback' }) {
  if (source === 'ipca') {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger>
            <Badge variant="outline" className="text-xs gap-1">
              IPCA <Info className="h-3 w-3" />
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <p>Índice oficial de inflação (IBGE)</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger>
          <Badge variant="outline" className="text-xs gap-1 border-yellow-400 text-yellow-700">
            Manual <Info className="h-3 w-3" />
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>IPCA indisponível — usando taxa configurada em Settings</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface SimulationCardProps {
  alert: RentAdjustmentAlert;
  onAdjust: (alert: RentAdjustmentAlert) => void;
}

function SimulationCard({ alert, onAdjust }: SimulationCardProps) {
  const adjustmentAmount = alert.new_value - alert.rental_value;

  return (
    <div
      className={`rounded-lg border p-4 transition-colors ${
        alert.status === 'overdue'
          ? 'border-destructive/30 bg-destructive/5'
          : 'border-yellow-400/30 bg-yellow-50/5'
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-3">
          {/* Header */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold">{alert.apartment}</span>
            <span className="text-muted-foreground text-sm">— {alert.tenant}</span>
            <StatusBadge alert={alert} />
            <IpcaSourceBadge source={alert.ipca_source} />
            {alert.prepaid_warning && <Badge variant="outline">Pré-pago</Badge>}
          </div>

          {/* Simulation */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="text-center">
              <div className="text-xs text-muted-foreground">Valor atual</div>
              <div className="text-sm font-medium">{formatCurrency(alert.rental_value)}</div>
            </div>
            <div className="text-center">
              <div className="text-xs text-muted-foreground">
                Reajuste ({alert.ipca_percentage.toFixed(2)}%)
              </div>
              <div className="text-sm font-medium text-yellow-600">
                + {formatCurrency(adjustmentAmount)}
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <div className="text-center">
              <div className="text-xs text-muted-foreground">Novo valor</div>
              <div className="text-sm font-bold text-success">
                {formatCurrency(alert.new_value)}
              </div>
            </div>
          </div>

          {/* Dates */}
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <CalendarDays className="h-3 w-3" />
              <span>Último reajuste: {formatDateBR(alert.last_rent_increase_date)}</span>
            </div>
            <div className="flex items-center gap-1">
              <CalendarDays className="h-3 w-3" />
              <span>Vencimento: {formatDateBR(alert.eligible_date)}</span>
            </div>
          </div>
        </div>

        <Button variant="default" size="sm" onClick={() => onAdjust(alert)}>
          <TrendingUp className="h-4 w-4 mr-1" />
          Reajustar
        </Button>
      </div>
    </div>
  );
}

interface ConfirmModalProps {
  open: boolean;
  alert: RentAdjustmentAlert | null;
  onClose: () => void;
}

function ConfirmAdjustmentModal({ open, alert, onClose }: ConfirmModalProps) {
  const applyMutation = useApplyRentAdjustment();
  const today = new Date().toISOString().slice(0, 10);
  const [renewalDate, setRenewalDate] = useState(today);
  const [newValue, setNewValue] = useState('');

  // Reset state when alert changes
  const alertId = alert?.lease_id;
  const [prevAlertId, setPrevAlertId] = useState<number | undefined>();
  if (alertId !== prevAlertId) {
    setPrevAlertId(alertId);
    if (alert) {
      setNewValue(alert.new_value.toFixed(2));
      setRenewalDate(today);
    }
  }

  if (!alert) return null;

  const parsedNewValue = parseFloat(newValue) || 0;
  const actualPercentage =
    alert.rental_value > 0
      ? (((parsedNewValue - alert.rental_value) / alert.rental_value) * 100).toFixed(2)
      : '0.00';

  const handleConfirm = async () => {
    if (parsedNewValue <= 0) {
      toast.error('Valor inválido');
      return;
    }

    const percentage = ((parsedNewValue / alert.rental_value - 1) * 100);

    try {
      await applyMutation.mutateAsync({
        leaseId: alert.lease_id,
        percentage,
        update_apartment_prices: true,
        renewal_date: renewalDate,
      });
      toast.success(
        `Reajuste aplicado: ${alert.apartment} — ${formatCurrency(alert.rental_value)} → ${formatCurrency(parsedNewValue)}`
      );
      onClose();
    } catch (error) {
      handleError(error, 'Erro ao aplicar reajuste');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Confirmar Reajuste</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Lease info */}
          <div className="rounded-lg border bg-muted/30 p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Imóvel</span>
              <span className="font-medium">{alert.apartment}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Inquilino</span>
              <span className="font-medium">{alert.tenant}</span>
            </div>
          </div>

          {/* IPCA percentage (read-only) */}
          <div className="rounded-lg border bg-muted/30 p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Valor atual</span>
              <span>{formatCurrency(alert.rental_value)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <div className="flex items-center gap-1 text-muted-foreground">
                <span>
                  {alert.ipca_source === 'ipca' ? 'IPCA' : 'Taxa manual'} (
                  {alert.ipca_percentage.toFixed(2)}%)
                </span>
              </div>
              <span className="text-yellow-600">
                + {formatCurrency(alert.new_value - alert.rental_value)}
              </span>
            </div>
          </div>

          {/* Editable new value */}
          <div>
            <Label htmlFor="new_value">Novo Valor (R$)</Label>
            <Input
              id="new_value"
              type="number"
              step="0.01"
              min="0"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              className="mt-1"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Percentual efetivo: {actualPercentage}% — Edite para arredondar se necessário
            </p>
          </div>

          {/* Renewal date */}
          <div>
            <Label htmlFor="renewal_date">Data de Renovação</Label>
            <Input
              id="renewal_date"
              type="date"
              value={renewalDate}
              onChange={(e) => setRenewalDate(e.target.value)}
              className="mt-1"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Referência para o próximo reajuste anual
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={applyMutation.isPending}
          >
            Cancelar
          </Button>
          <Button onClick={handleConfirm} disabled={applyMutation.isPending}>
            <TrendingUp className="h-4 w-4 mr-2" />
            {applyMutation.isPending ? 'Aplicando...' : 'Confirmar Reajuste'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RentAdjustmentAlerts() {
  const { data, isLoading } = useRentAdjustmentAlerts();
  const [selectedAlert, setSelectedAlert] = useState<RentAdjustmentAlert | null>(null);

  if (isLoading) return null;

  if (!data || data.alerts.length === 0) {
    return (
      <Alert className="border-success/20 bg-success/10">
        <CheckCircle2 className="h-4 w-4 text-success" />
        <AlertDescription className="text-success-foreground">
          Nenhum reajuste pendente. Todos os contratos estão em dia.
        </AlertDescription>
      </Alert>
    );
  }

  const hasPartialIpca = data.alerts.some((a) => a.ipca_source === 'fallback');
  const ipcaMonth = data.ipcaLatestMonth
    ? format(parseISO(data.ipcaLatestMonth), 'MMMM/yyyy', { locale: ptBR })
    : null;

  return (
    <>
      <Accordion type="single" collapsible>
        <AccordionItem
          value="rent-adjustments"
          className="border-yellow-400/30 rounded-lg border"
        >
          <AccordionTrigger className="px-6 py-4 hover:no-underline">
            <div className="mr-4 flex w-full items-center gap-2">
              <TrendingUp className="h-5 w-5 text-yellow-600" />
              <span className="text-lg font-semibold">Reajustes Pendentes</span>
              <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">
                {data.alerts.length}
              </Badge>
              {ipcaMonth && (
                <span className="ml-auto text-xs text-muted-foreground">
                  IPCA: {ipcaMonth}
                </span>
              )}
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-6 pb-4">
            {hasPartialIpca && (
              <div className="mb-4 rounded-md border border-yellow-400/30 bg-yellow-50/10 p-3 text-sm text-yellow-700">
                Alguns contratos usam a taxa manual de{' '}
                <a href="/settings" className="font-medium underline">
                  Configurações
                </a>{' '}
                porque o IPCA do período ainda não foi publicado pelo IBGE.
              </div>
            )}
            <div className="space-y-3">
              {data.alerts.map((alert) => (
                <SimulationCard
                  key={alert.lease_id}
                  alert={alert}
                  onAdjust={setSelectedAlert}
                />
              ))}
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <ConfirmAdjustmentModal
        open={selectedAlert !== null}
        alert={selectedAlert}
        onClose={() => setSelectedAlert(null)}
      />
    </>
  );
}
