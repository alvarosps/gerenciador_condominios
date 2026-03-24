'use client';

import { useState } from 'react';
import { Pencil, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ExpenseDetailItem } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';

const ITEMS_PER_PAGE = 10;

export function ExpenseDetailTable({
  items,
  onEdit,
  onDelete,
}: {
  items: ExpenseDetailItem[];
  onEdit: (item: ExpenseDetailItem) => void;
  onDelete: (item: ExpenseDetailItem) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const hasMore = items.length > ITEMS_PER_PAGE;
  const visibleItems = showAll ? items : items.slice(0, ITEMS_PER_PAGE);

  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="py-2 px-2 text-xs font-medium text-muted-foreground">Descrição</th>
            <th className="py-2 px-2 text-xs font-medium text-muted-foreground">Cartão</th>
            <th className="py-2 px-2 text-xs font-medium text-muted-foreground text-center">
              Parcela Atual
            </th>
            <th className="py-2 px-2 text-xs font-medium text-muted-foreground text-center">
              Total Parcelas
            </th>
            <th className="py-2 px-2 text-xs font-medium text-muted-foreground">Categoria</th>
            <th className="py-2 px-2 text-xs font-medium text-muted-foreground">Subcategoria</th>
            <th className="py-2 px-2 text-xs font-medium text-muted-foreground">Notas</th>
            <th className="py-2 px-2 text-xs font-medium text-muted-foreground text-right">
              Valor
            </th>
            <th className="py-2 px-2 text-xs font-medium text-muted-foreground text-center">
              Ações
            </th>
          </tr>
        </thead>
        <tbody>
          {visibleItems.map((item, i) => (
            <tr
              key={item.installment_id ?? `exp-${item.expense_id}-${i}`}
              className="border-b hover:bg-muted/30"
            >
              <td className="py-2 px-2 max-w-[200px] truncate">{item.description}</td>
              <td className="py-2 px-2 text-muted-foreground">{item.card_name ?? '—'}</td>
              <td className="py-2 px-2 text-center text-muted-foreground">
                {item.installment_number ?? '—'}
              </td>
              <td className="py-2 px-2 text-center text-muted-foreground">
                {item.total_installments ?? '—'}
              </td>
              <td className="py-2 px-2">
                {item.category_name ? (
                  <span
                    className="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
                    style={{
                      backgroundColor: `${item.category_color ?? '#6b7280'}20`,
                      color: item.category_color ?? '#6b7280',
                    }}
                  >
                    {item.category_name}
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </td>
              <td className="py-2 px-2 text-muted-foreground text-xs">
                {item.subcategory_name ?? '—'}
              </td>
              <td className="py-2 px-2 text-muted-foreground text-xs max-w-[120px] truncate">
                {item.notes ?? '—'}
              </td>
              <td className="py-2 px-2 text-right font-medium text-red-600">
                {formatCurrency(item.amount)}
              </td>
              <td className="py-2 px-2 text-center">
                <div className="flex items-center justify-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => onEdit(item)}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-red-600 hover:text-red-700"
                    onClick={() => onDelete(item)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {hasMore && !showAll && (
        <button
          type="button"
          onClick={() => setShowAll(true)}
          className="w-full text-center text-sm text-blue-600 hover:underline py-3"
        >
          Ver todos ({items.length} itens)
        </button>
      )}
    </div>
  );
}
