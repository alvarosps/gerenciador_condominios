'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { ExpenseDetailItem } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';
import { ExpenseDetailTable } from './expense-detail-table';

function SubAccordion({
  title,
  items,
  total,
  onEdit,
  onDelete,
  readonly = false,
  onMarkPaid,
  isMarkingPaid = false,
}: {
  title: string;
  items: ExpenseDetailItem[];
  total: number;
  onEdit: (item: ExpenseDetailItem) => void;
  onDelete: (item: ExpenseDetailItem) => void;
  readonly?: boolean;
  onMarkPaid?: (item: ExpenseDetailItem) => void;
  isMarkingPaid?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border rounded-md bg-muted/10">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center justify-between w-full px-3 py-2.5 hover:bg-muted/30 transition-colors text-sm"
      >
        <div className="flex items-center gap-2">
          {isOpen ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          )}
          <span className="font-medium">{title}</span>
          <span className="text-xs text-muted-foreground">({items.length} itens)</span>
        </div>
        <span className="font-semibold text-destructive">{formatCurrency(total)}</span>
      </button>

      {isOpen && (
        <div className="px-3 pb-3">
          <ExpenseDetailTable items={items} onEdit={onEdit} onDelete={onDelete} readonly={readonly} onMarkPaid={onMarkPaid} isMarkingPaid={isMarkingPaid} />
        </div>
      )}
    </div>
  );
}

function groupItemsByField(
  items: ExpenseDetailItem[],
  field: keyof ExpenseDetailItem,
): { label: string; items: ExpenseDetailItem[]; total: number }[] {
  const map = new Map<string, { items: ExpenseDetailItem[]; total: number }>();

  for (const item of items) {
    const key = String(item[field] ?? 'Outros');
    if (!map.has(key)) {
      map.set(key, { items: [], total: 0 });
    }
    const group = map.get(key);
    if (group) {
      group.items.push(item);
      group.total += item.amount;
    }
  }

  return [...map.entries()]
    .map(([label, data]) => ({ label, ...data }))
    .sort((a, b) => b.total - a.total);
}

export function ExpenseAccordion({
  title,
  color,
  items,
  total,
  onEdit,
  onDelete,
  defaultOpen = false,
  groupBy,
  readonly = false,
  onMarkPaid,
  isMarkingPaid = false,
}: {
  title: string;
  color: string;
  items: ExpenseDetailItem[];
  total: number;
  onEdit: (item: ExpenseDetailItem) => void;
  onDelete: (item: ExpenseDetailItem) => void;
  defaultOpen?: boolean;
  groupBy?: keyof ExpenseDetailItem;
  readonly?: boolean;
  onMarkPaid?: (item: ExpenseDetailItem) => void;
  isMarkingPaid?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (items.length === 0 && total === 0) return null;

  const groups = groupBy ? groupItemsByField(items, groupBy) : null;

  return (
    <div className="border rounded-lg">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center justify-between w-full p-4 hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isOpen ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          <span className={cn('font-semibold', color)}>{title}</span>
          <span className="text-xs text-muted-foreground">({items.length} itens)</span>
        </div>
        <span className={cn('font-bold', color)}>{formatCurrency(total)}</span>
      </button>

      {isOpen && (
        <div className="px-4 pb-4 space-y-2">
          {groups ? (
            groups.map((group) => (
              <SubAccordion
                key={group.label}
                title={group.label}
                items={group.items}
                total={group.total}
                onEdit={onEdit}
                onDelete={onDelete}
                readonly={readonly}
                onMarkPaid={onMarkPaid}
                isMarkingPaid={isMarkingPaid}
              />
            ))
          ) : (
            <ExpenseDetailTable items={items} onEdit={onEdit} onDelete={onDelete} readonly={readonly} onMarkPaid={onMarkPaid} isMarkingPaid={isMarkingPaid} />
          )}
        </div>
      )}
    </div>
  );
}
