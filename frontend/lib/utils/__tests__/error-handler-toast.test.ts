import { describe, it, expect, vi, beforeEach } from 'vitest';
import { toast } from 'sonner';
import { showFinanceMutationError } from '../error-handler';

/**
 * Helper to create a realistic AxiosError with a given status and response data — mirrors
 * error-handler.test.ts's makeAxiosError (same shape, no library mock, only the isAxiosError
 * marker property axios itself checks for).
 */
function makeAxiosError(status?: number, data?: Record<string, unknown>): unknown {
  const error = new Error('Request failed') as Error & {
    isAxiosError: boolean;
    response?: { status: number; data: Record<string, unknown> };
  };
  error.isAxiosError = true;
  if (status !== undefined) {
    error.response = { status, data: data ?? {} };
  }
  return error;
}

describe('showFinanceMutationError', () => {
  beforeEach(() => {
    vi.mocked(toast.error).mockReset();
  });

  it('shows an actionable toast with "Abrir fechamento" for a 400 whose message mentions mês fechado', () => {
    const goToMonthClose = vi.fn();
    const error = makeAxiosError(400, { detail: 'Competência 06/2026 está fechada.' });

    showFinanceMutationError(error, 'Erro ao pagar conta', goToMonthClose);

    expect(toast.error).toHaveBeenCalledWith(
      'Competência 06/2026 está fechada.',
      expect.objectContaining({
        action: expect.objectContaining({ label: 'Abrir fechamento' }) as unknown,
      })
    );

    // The action's onClick navigates to the month-close page — never called yet, but wired.
    const call = vi.mocked(toast.error).mock.calls[0];
    const options = call?.[1] as { action?: { onClick: () => void } } | undefined;
    options?.action?.onClick();
    expect(goToMonthClose).toHaveBeenCalledOnce();
  });

  it('matches the real backend closed-month message ("Este mês está fechado e não aceita lançamentos.")', () => {
    const goToMonthClose = vi.fn();
    const error = makeAxiosError(400, {
      detail: 'Este mês está fechado e não aceita lançamentos.',
    });

    showFinanceMutationError(error, 'Erro ao pagar conta', goToMonthClose);

    expect(toast.error).toHaveBeenCalledWith(
      'Este mês está fechado e não aceita lançamentos.',
      expect.objectContaining({
        action: expect.objectContaining({ label: 'Abrir fechamento' }) as unknown,
      })
    );
  });

  it('falls back to the plain handleError toast for non-closed-month errors', () => {
    const goToMonthClose = vi.fn();
    const error = makeAxiosError(400, { detail: 'Valor inválido' });

    showFinanceMutationError(error, 'Erro ao pagar conta', goToMonthClose);

    expect(toast.error).toHaveBeenCalledWith('Valor inválido');
    const call = vi.mocked(toast.error).mock.calls[0];
    expect(call?.[1]).toBeUndefined();
  });

  it('does not add an action for a non-400 error even if the message mentions "fechad"', () => {
    const goToMonthClose = vi.fn();
    const error = makeAxiosError(500, { detail: 'Conta fechada permanentemente.' });

    showFinanceMutationError(error, 'Erro ao pagar conta', goToMonthClose);

    const call = vi.mocked(toast.error).mock.calls[0];
    expect(call?.[1]).toBeUndefined();
  });

  it('uses the PT fallback when the error carries no message', () => {
    const goToMonthClose = vi.fn();

    showFinanceMutationError(undefined, 'Erro ao pagar conta', goToMonthClose);

    expect(toast.error).toHaveBeenCalledWith('Erro ao pagar conta');
  });
});
