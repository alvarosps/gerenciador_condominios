import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { MonthCloseActionDialog } from '../_components/month-close-action-dialog';
import { createMockCondoMonthClose } from '@/tests/mocks/data/finances';

describe('MonthCloseActionDialog', () => {
  const may = createMockCondoMonthClose({ reference_month: '2026-05-01', status: 'open' });

  it('renders the close title with the competência via formatMonthYear and confirms', () => {
    const onConfirm = vi.fn();
    renderWithProviders(
      <MonthCloseActionDialog
        open
        close={may}
        action="close"
        isPending={false}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText(/Fechar mês: Maio de 2026/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Fechar mês' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('renders the reopen title and confirms in reopen mode', () => {
    const onConfirm = vi.fn();
    renderWithProviders(
      <MonthCloseActionDialog
        open
        close={createMockCondoMonthClose({ reference_month: '2026-05-01', status: 'closed' })}
        action="reopen"
        isPending={false}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText(/Reabrir mês: Maio de 2026/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Reabrir mês' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('disables the actions while pending (no double submit)', () => {
    renderWithProviders(
      <MonthCloseActionDialog
        open
        close={may}
        action="close"
        isPending
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', { name: 'Aguarde...' })).toBeDisabled();
  });
});
