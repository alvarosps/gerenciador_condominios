'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { formatCurrency } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';
import { QuickPaymentModal } from '@/app/(dashboard)/financial/_components/quick-payment-modal';

export function DetailHeader({
  title,
  total,
  totalPaid,
  pending,
  isPayable,
  personId,
  monthLabel,
  year,
  month,
}: {
  title: string;
  total: number;
  totalPaid?: number;
  pending?: number;
  isPayable?: boolean;
  personId?: number;
  monthLabel: string;
  year: number;
  month: number;
}) {
  const [paymentOpen, setPaymentOpen] = useState(false);
  const progress =
    total > 0 && totalPaid !== null && totalPaid !== undefined
      ? Math.min((totalPaid / total) * 100, 100)
      : 0;
  const isPaid = pending !== null && pending !== undefined && pending <= 0;

  return (
    <div className="space-y-4">
      {/* Back link */}
      <Link
        href={`/financial/expenses?year=${year}&month=${month}`}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Voltar para Despesas
      </Link>

      {/* Header row */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="text-muted-foreground text-sm">{monthLabel}</p>
        </div>
        <div className="text-right space-y-2">
          <div className="text-2xl font-bold text-red-600">{formatCurrency(total)}</div>

          {isPayable && totalPaid !== null && totalPaid !== undefined && pending !== null && pending !== undefined && (
            <>
              <div className="w-48 bg-gray-200 rounded-full h-2.5">
                <div
                  className={cn(
                    'h-2.5 rounded-full transition-all',
                    isPaid ? 'bg-green-500' : progress > 50 ? 'bg-blue-500' : 'bg-amber-500',
                  )}
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Pago: {formatCurrency(totalPaid)} ·{' '}
                {isPaid ? 'Quitado' : `Restante: ${formatCurrency(pending)}`}
              </p>
              {!isPaid && personId && (
                <Button size="sm" className="mt-1" onClick={() => setPaymentOpen(true)}>
                  Registrar Pagamento
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {personId && (
        <QuickPaymentModal
          open={paymentOpen}
          onClose={() => setPaymentOpen(false)}
          personId={personId}
          personName={title}
          year={year}
          month={month}
        />
      )}
    </div>
  );
}
