'use client';

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Loader2 } from 'lucide-react';
import { useRentAdjustments } from '@/lib/api/hooks/use-rent-adjustments';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';

interface Props {
  open: boolean;
  leaseId: number | null;
  onClose: () => void;
}

export function RentAdjustmentHistorySheet({ open, leaseId, onClose }: Props) {
  const { data: adjustments, isLoading } = useRentAdjustments(leaseId);

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Histórico de Reajustes</SheetTitle>
        </SheetHeader>

        <div className="mt-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : !adjustments || adjustments.length === 0 ? (
            <p className="text-center text-muted-foreground py-12">
              Nenhum reajuste registrado
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="pb-2 text-left font-medium">Data</th>
                    <th className="pb-2 text-right font-medium">Percentual</th>
                    <th className="pb-2 text-right font-medium">Valor Anterior</th>
                    <th className="pb-2 text-right font-medium">Valor Novo</th>
                    <th className="pb-2 text-center font-medium">Apt. Atualizado</th>
                    <th className="pb-2 text-left font-medium pl-4">Aplicado por</th>
                  </tr>
                </thead>
                <tbody>
                  {adjustments.map((adj) => (
                    <tr key={adj.id} className="border-b last:border-0 hover:bg-muted/40">
                      <td className="py-3">{formatDate(adj.adjustment_date)}</td>
                      <td className="py-3 text-right">
                        <span
                          className={
                            adj.percentage > 0
                              ? 'text-success'
                              : adj.percentage < 0
                                ? 'text-destructive'
                                : ''
                          }
                        >
                          {adj.percentage > 0 ? '+' : ''}
                          {adj.percentage.toFixed(2)}%
                        </span>
                      </td>
                      <td className="py-3 text-right">{formatCurrency(adj.previous_value)}</td>
                      <td className="py-3 text-right font-medium">{formatCurrency(adj.new_value)}</td>
                      <td className="py-3 text-center">
                        {adj.apartment_updated ? (
                          <span className="text-success font-medium">Sim</span>
                        ) : (
                          <span className="text-muted-foreground">Não</span>
                        )}
                      </td>
                      <td className="py-3 pl-4 text-muted-foreground">
                        {adj.created_by ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
