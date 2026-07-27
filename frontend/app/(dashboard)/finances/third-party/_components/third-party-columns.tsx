'use client';

import Link from 'next/link';
import { type Column } from '@/components/tables/data-table';
import { ROUTES } from '@/lib/utils/constants';
import { dueDateLabel, formatCurrency } from '@/lib/utils/formatters';
import type { ThirdPartyPerson } from '@/lib/schemas/finances/third-party.schema';

/**
 * The name cell is an explicit link — `DataTable` has no `onRowClick` and must not grow one for
 * this screen (same precedent as `account-columns.tsx`).
 */
export function buildThirdPartyColumns(): Column<ThirdPartyPerson>[] {
  return [
    {
      title: 'Pessoa',
      key: 'person_name',
      primary: true,
      sorter: (a, b) => a.person_name.localeCompare(b.person_name),
      render: (_, record) => (
        <Link
          href={`${ROUTES.FINANCES_THIRD_PARTY}/${String(record.person_id)}`}
          className="text-primary underline-offset-4 hover:underline"
        >
          {record.person_name}
        </Link>
      ),
    },
    {
      title: 'Devido em aberto',
      key: 'total_em_aberto',
      align: 'right',
      sorter: (a, b) => a.total_em_aberto - b.total_em_aberto,
      render: (_, record) => (
        <span className="font-semibold tabular-nums">{formatCurrency(record.total_em_aberto)}</span>
      ),
    },
    {
      title: 'Atrasado',
      key: 'total_atrasado',
      align: 'right',
      sorter: (a, b) => a.total_atrasado - b.total_atrasado,
      render: (_, record) => (
        <span
          className={
            record.total_atrasado > 0
              ? 'font-semibold tabular-nums text-destructive'
              : 'tabular-nums'
          }
        >
          {formatCurrency(record.total_atrasado)}
        </span>
      ),
    },
    {
      title: 'Último acerto',
      key: 'last_settlement_date',
      render: (_, record) =>
        record.last_settlement_date === null ? (
          <span className="text-muted-foreground">—</span>
        ) : (
          dueDateLabel(record.last_settlement_date)
        ),
    },
  ];
}
