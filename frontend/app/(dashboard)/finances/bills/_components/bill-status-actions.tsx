'use client';

import { Ban, CalendarClock, PauseCircle, PlayCircle } from 'lucide-react';
import { toast } from 'sonner';
import { DropdownMenuItem } from '@/components/ui/dropdown-menu';
import {
  useCancelBill,
  useDeferBill,
  useReactivateBill,
  useSuspendBill,
} from '@/lib/api/hooks/use-bills';
import { handleError } from '@/lib/utils/error-handler';
import type { Bill } from '@/lib/schemas/finances/bill.schema';

interface BillStatusActionsProps {
  bill: Bill;
}

/**
 * Lifecycle transition menu items, conditional on the bill's current lifecycle_state.
 * Active bills can be suspended/deferred/canceled; non-active bills can be reactivated.
 */
export function BillStatusActions({ bill }: BillStatusActionsProps) {
  const suspend = useSuspendBill();
  const defer = useDeferBill();
  const cancel = useCancelBill();
  const reactivate = useReactivateBill();

  if (bill.id === undefined) return null;
  const billId = bill.id;

  function run(
    action: { mutate: typeof suspend.mutate },
    successMessage: string,
    errorContext: string,
  ) {
    action.mutate(billId, {
      onSuccess: () => {
        toast.success(successMessage);
      },
      onError: (error) => {
        handleError(error, errorContext);
      },
    });
  }

  const isActive = bill.lifecycle_state === 'active';

  return (
    <>
      {isActive ? (
        <>
          <DropdownMenuItem onClick={() => run(suspend, 'Conta suspensa', 'Erro ao suspender conta')}>
            <PauseCircle className="mr-2 h-4 w-4" />
            Suspender
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => run(defer, 'Conta adiada', 'Erro ao adiar conta')}>
            <CalendarClock className="mr-2 h-4 w-4" />
            Deferir
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => run(cancel, 'Conta cancelada', 'Erro ao cancelar conta')}>
            <Ban className="mr-2 h-4 w-4" />
            Cancelar
          </DropdownMenuItem>
        </>
      ) : (
        <DropdownMenuItem
          onClick={() => run(reactivate, 'Conta reativada', 'Erro ao reativar conta')}
        >
          <PlayCircle className="mr-2 h-4 w-4" />
          Reativar
        </DropdownMenuItem>
      )}
    </>
  );
}
