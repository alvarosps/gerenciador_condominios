'use client';

import { useTerminationFee } from '@/lib/api/hooks/use-leases';
import { formatCurrency } from '@/lib/utils/formatters';

export function TerminationFeeEstimate({ leaseId }: { leaseId: number }) {
  const fee = useTerminationFee(leaseId);
  return (
    <div role="status" className="space-y-2 text-sm">
      <p>
        Multa estimada para saída hoje:{' '}
        {fee.isFetching
          ? 'Calculando...'
          : fee.isError
            ? 'Cálculo indisponível'
            : fee.data !== undefined
              ? formatCurrency(Number(fee.data))
              : '—'}
      </p>
      <p className="text-muted-foreground">
        2,5 aluguéis, com redução proporcional em 12 meses. Confira o contrato assinado e as
        hipóteses legais de dispensa. Encerrar não gera cobrança automática da multa.
      </p>
    </div>
  );
}
