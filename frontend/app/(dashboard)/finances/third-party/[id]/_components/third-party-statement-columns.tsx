'use client';

import { ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { type Column } from '@/components/tables/data-table';
import { competenceMonthLabel, dueDateLabel, formatCurrency } from '@/lib/utils/formatters';
import {
  THIRD_PARTY_ITEM_KIND_LABELS,
  type ThirdPartyStatementMonth,
} from '@/lib/schemas/finances/third-party.schema';
import { ThirdPartyStatusChip } from './third-party-status-chip';

interface BuildStatementColumnsOptions {
  expandedMonths: ReadonlySet<string>;
  onToggleMonth: (month: string) => void;
}

/**
 * The per-month detail is rendered INSIDE the month cell rather than as an extra table row:
 * `DataTable` owns its row rendering and has no expandable-row API, and extending it for this one
 * screen is explicitly out of scope. Living in the cell also means the detail shows up unchanged
 * in the mobile card surface, which reuses the very same `render`.
 */
export function buildThirdPartyStatementColumns({
  expandedMonths,
  onToggleMonth,
}: BuildStatementColumnsOptions): Column<ThirdPartyStatementMonth>[] {
  return [
    {
      title: 'Mês',
      key: 'month',
      primary: true,
      render: (_, record) => {
        const label = competenceMonthLabel(record.month);
        const isExpanded = expandedMonths.has(record.month);
        const hasItems = record.items.length > 0;
        return (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-1">
              {hasItems ? (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  aria-label={`Detalhes de ${label}`}
                  aria-expanded={isExpanded}
                  onClick={() => onToggleMonth(record.month)}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </Button>
              ) : (
                <span className="inline-block h-6 w-6" aria-hidden="true" />
              )}
              <span>{label}</span>
            </div>

            {isExpanded && hasItems && (
              <ul className="ml-7 space-y-1 border-l pl-3 text-xs text-muted-foreground">
                {record.items.map((item) => (
                  <li key={`${item.kind}-${String(item.id)}`} className="flex flex-wrap gap-2">
                    <span className="font-medium text-foreground">{item.description}</span>
                    <span>{THIRD_PARTY_ITEM_KIND_LABELS[item.kind]}</span>
                    <span>{dueDateLabel(item.date)}</span>
                    <span className="tabular-nums">{formatCurrency(item.amount)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      },
    },
    {
      title: 'Devido',
      key: 'devido',
      align: 'right',
      render: (_, record) => formatCurrency(record.devido),
    },
    {
      title: 'Aplicado',
      key: 'aplicado',
      align: 'right',
      render: (_, record) => formatCurrency(record.aplicado),
    },
    {
      title: 'Resto',
      key: 'resto',
      align: 'right',
      render: (_, record) => formatCurrency(record.resto),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, record) => <ThirdPartyStatusChip status={record.status} />,
    },
  ];
}
