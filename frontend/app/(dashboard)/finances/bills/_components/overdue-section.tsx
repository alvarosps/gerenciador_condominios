'use client';

import { HandCoins } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable, type Column } from '@/components/tables/data-table';
import { formatCurrency, getTodayLocalISO } from '@/lib/utils/formatters';
import type { Bill } from '@/lib/schemas/finances/bill.schema';
import type { MonthBoard } from '@/lib/schemas/finances/month-board.schema';
import type { ConsolidableBill } from '../../accounts/[id]/_components/consolidate-debt-dialog';

const SIXTY_DAYS = 60;

/**
 * Derives the S73 `ConsolidateDebtDialog`'s `bills` prop (S75 contract) from the board: every bill
 * across the board's sections whose `billing_account.id` matches, mapped `id → bill_id`. Scans all
 * sections (not just deferred_suspended) because an account's open debt can legitimately span
 * Atrasadas / deferred_suspended / groups — the CTA only triggers from the deferred/suspended row,
 * but the plan should cover the account's whole open balance, mirroring the extrato's dialog (S73).
 */
export function toConsolidableBills(board: MonthBoard, accountId: number): ConsolidableBill[] {
  const allBills = [
    ...board.overdue,
    ...board.deferred_suspended,
    ...board.groups.flatMap((group) => group.bills),
  ];
  const seen = new Set<number>();
  const result: ConsolidableBill[] = [];
  for (const bill of allBills) {
    if (bill.id === undefined || bill.billing_account?.id !== accountId) continue;
    if (seen.has(bill.id)) continue;
    seen.add(bill.id);
    result.push({
      bill_id: bill.id,
      description: bill.description,
      competence_month: bill.competence_month,
      due_date: bill.due_date,
      amount_remaining: bill.amount_remaining ?? 0,
    });
  }
  return result;
}

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

/** Whether the row offers the "Parcelar" CTA — consolidation is per-account, so a bill without a
 *  `billing_account` has nothing to consolidate into (S75 contract). */
export function canConsolidate(bill: Bill): boolean {
  return bill.billing_account !== null && bill.billing_account !== undefined;
}

/** Adds the "Parcelar" CTA — deferred/suspended sub-section ONLY (never Atrasadas, S75 contract),
 *  and only on rows with a `billing_account` (consolidation is per-account). */
function buildDeferredSuspendedColumns(
  columns: Column<Bill>[],
  onConsolidate: (bill: Bill) => void
): Column<Bill>[] {
  return [
    ...columns,
    {
      title: '',
      key: 'consolidate',
      render: (_, record) =>
        canConsolidate(record) ? (
          <Button variant="outline" size="sm" onClick={() => onConsolidate(record)}>
            <HandCoins className="mr-2 h-4 w-4" />
            Parcelar
          </Button>
        ) : null,
    },
  ];
}

interface OverdueSectionProps {
  overdue: Bill[];
  deferredSuspended: Bill[];
  columns: Column<Bill>[];
  overdueTotal: string;
  onConsolidate: (bill: Bill) => void;
  today?: string;
}

/**
 * Fixed, non-collapsible "Atrasadas" card (cross-competence, above the accordion) plus the
 * "Dívida adiada/suspensa" sub-section (excluded from the month totals). Renders null when both
 * lists are empty (S74 contract). The state badge ("Suspensa"/"Adiada") comes from the shared
 * Status column (`BillStatusChip` — single source of truth for lifecycle labels, DRY) rather
 * than a duplicate column here. The "Parcelar" CTA (S75) is added only to the deferred/suspended
 * table via its own columns array — Atrasadas never gets it.
 */
export function OverdueSection({
  overdue,
  deferredSuspended,
  columns,
  overdueTotal,
  onConsolidate,
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
            columns={buildDeferredSuspendedColumns(columns, onConsolidate)}
            dataSource={deferredSuspended}
            rowKey="id"
            pagination={false}
          />
        </CardContent>
      )}
    </Card>
  );
}
