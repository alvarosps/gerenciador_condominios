'use client';

import { useState } from 'react';
import { AlertTriangle, CheckCircle, ChevronDown, ChevronRight, Pencil, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import type { ExpenseDetailItem } from '@/lib/api/hooks/use-financial-dashboard';
import { useMarkInstallmentPaid } from '@/lib/api/hooks/use-expense-installments';
import { formatCurrency } from '@/lib/utils/formatters';

interface OverdueSectionProps {
  items: ExpenseDetailItem[];
  total: number;
  onEdit: (item: ExpenseDetailItem) => void;
  onDelete: (item: ExpenseDetailItem) => void;
  onPaid?: () => void;
}

export function OverdueSection({ items, total, onEdit, onDelete, onPaid }: OverdueSectionProps) {
  const [isOpen, setIsOpen] = useState(true);
  const markPaidMutation = useMarkInstallmentPaid();

  if (items.length === 0) return null;

  const handleMarkPaid = async (item: ExpenseDetailItem) => {
    if (!item.installment_id) return;
    try {
      await markPaidMutation.mutateAsync(item.installment_id);
      toast.success(`"${item.description}" marcada como paga`);
      onPaid?.();
    } catch {
      toast.error('Erro ao marcar como paga');
    }
  };

  return (
    <div className="border-2 border-destructive/30 rounded-lg bg-destructive/5">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center justify-between w-full p-4 hover:bg-destructive/10 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isOpen ? (
            <ChevronDown className="h-4 w-4 text-destructive" />
          ) : (
            <ChevronRight className="h-4 w-4 text-destructive" />
          )}
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <span className="font-semibold text-destructive">Valores em Atraso</span>
          <Badge variant="destructive" className="text-xs">
            {items.length} {items.length === 1 ? 'parcela' : 'parcelas'}
          </Badge>
        </div>
        <span className="font-bold text-destructive">{formatCurrency(total)}</span>
      </button>

      {isOpen && (
        <div className="px-4 pb-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2 px-2 text-xs font-medium text-muted-foreground">Descrição</th>
                <th className="py-2 px-2 text-xs font-medium text-muted-foreground">Prédio</th>
                <th className="py-2 px-2 text-xs font-medium text-muted-foreground text-center">
                  Parcela
                </th>
                <th className="py-2 px-2 text-xs font-medium text-muted-foreground">Vencimento</th>
                <th className="py-2 px-2 text-xs font-medium text-muted-foreground text-center">
                  Dias em Atraso
                </th>
                <th className="py-2 px-2 text-xs font-medium text-muted-foreground text-right">
                  Valor
                </th>
                <th className="py-2 px-2 text-xs font-medium text-muted-foreground text-center">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.installment_id ?? `overdue-${item.expense_id}`}
                  className="border-b hover:bg-destructive/5"
                >
                  <td className="py-2 px-2 max-w-[200px] truncate">{item.description}</td>
                  <td className="py-2 px-2 text-muted-foreground">
                    {item.building_name ?? '—'}
                  </td>
                  <td className="py-2 px-2 text-center text-muted-foreground">
                    {item.installment_number !== null && item.installment_number !== undefined && item.total_installments !== null && item.total_installments !== undefined
                      ? `${item.installment_number}/${item.total_installments}`
                      : '—'}
                  </td>
                  <td className="py-2 px-2 text-muted-foreground">
                    {item.due_date
                      ? new Date(item.due_date + 'T00:00:00').toLocaleDateString('pt-BR')
                      : '—'}
                  </td>
                  <td className="py-2 px-2 text-center">
                    <Badge variant="destructive" className="text-xs">
                      {item.days_overdue ?? 0}d
                    </Badge>
                  </td>
                  <td className="py-2 px-2 text-right font-medium text-destructive">
                    {formatCurrency(item.amount)}
                  </td>
                  <td className="py-2 px-2 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-success hover:text-success/80"
                        onClick={() => void handleMarkPaid(item)}
                        disabled={markPaidMutation.isPending}
                        aria-label="Marcar como paga"
                      >
                        <CheckCircle className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => onEdit(item)}
                        aria-label="Editar"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive hover:text-destructive/80"
                        onClick={() => onDelete(item)}
                        aria-label="Excluir"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
