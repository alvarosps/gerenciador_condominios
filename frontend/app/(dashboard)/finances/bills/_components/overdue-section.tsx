'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable, type Column } from '@/components/tables/data-table';
import { formatCurrency, getTodayLocalISO } from '@/lib/utils/formatters';
import type { Bill } from '@/lib/schemas/finances/bill.schema';

const SIXTY_DAYS = 60;

/**
 * Days between a YYYY-MM-DD due_date and "today" (also YYYY-MM-DD), built via split — never
 * `new Date(iso)` (timezone pitfall, mirrors bill-columns.tsx competenceLabel/dueDateLabel).
 * Exported as a pure function so it is directly testable.
 */
export function daysLate(dueDate: string, today: string = getTodayLocalISO()): number {
  const [dueYear, dueMonth, dueDay] = dueDate.split('-').map(Number);
  const [todayYear, todayMonth, todayDay] = today.split('-').map(Number);
  const due = new Date(dueYear ?? 0, (dueMonth ?? 1) - 1, dueDay ?? 1);
  const now = new Date(todayYear ?? 0, (todayMonth ?? 1) - 1, todayDay ?? 1);
  const diffMs = now.getTime() - due.getTime();
  return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

/** "N dia(s)" below 60 days, "N mês(es)" from 60 days on (design §3.3). */
function daysLateLabel(days: number): string {
  if (days >= SIXTY_DAYS) {
    const months = Math.floor(days / 30);
    return `${String(months)} ${months === 1 ? 'mês' : 'meses'}`;
  }
  return `${String(days)} ${days === 1 ? 'dia' : 'dias'}`;
}

function buildOverdueColumns(columns: Column<Bill>[], today: string): Column<Bill>[] {
  return [
    ...columns,
    {
      title: 'Atraso',
      key: 'days-late',
      render: (_, record) => (
        <Badge variant="destructive">{daysLateLabel(daysLate(record.due_date, today))}</Badge>
      ),
    },
  ];
}

interface OverdueSectionProps {
  overdue: Bill[];
  deferredSuspended: Bill[];
  columns: Column<Bill>[];
  overdueTotal: string;
  today?: string;
}

/**
 * Fixed, non-collapsible "Atrasadas" card (cross-competence, above the accordion) plus the
 * "Dívida adiada/suspensa" sub-section (excluded from the month totals). Renders null when both
 * lists are empty (S74 contract). The state badge ("Suspensa"/"Adiada") comes from the shared
 * Status column (`BillStatusChip` — single source of truth for lifecycle labels, DRY) rather
 * than a duplicate column here.
 */
export function OverdueSection({
  overdue,
  deferredSuspended,
  columns,
  overdueTotal,
  today = getTodayLocalISO(),
}: OverdueSectionProps) {
  if (overdue.length === 0 && deferredSuspended.length === 0) {
    return null;
  }

  return (
    <Card className="mb-4 border-destructive/30">
      {overdue.length > 0 && (
        <>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div className="flex items-center gap-2">
              <CardTitle className="text-base">Atrasadas</CardTitle>
              <Badge variant="destructive">{overdue.length}</Badge>
            </div>
            <span className="text-sm font-medium tabular-nums">{formatCurrency(overdueTotal)}</span>
          </CardHeader>
          <CardContent>
            <DataTable<Bill>
              columns={buildOverdueColumns(columns, today)}
              dataSource={overdue}
              rowKey="id"
              pagination={false}
            />
          </CardContent>
        </>
      )}

      {deferredSuspended.length > 0 && (
        <CardContent className={overdue.length > 0 ? 'pt-0' : 'pt-6'}>
          <h3 className="mb-2 text-sm font-semibold">Dívida adiada/suspensa</h3>
          <p className="mb-2 text-xs text-muted-foreground">
            Estes valores não entram nos totais do mês.
          </p>
          <DataTable<Bill>
            columns={columns}
            dataSource={deferredSuspended}
            rowKey="id"
            pagination={false}
          />
        </CardContent>
      )}
    </Card>
  );
}
