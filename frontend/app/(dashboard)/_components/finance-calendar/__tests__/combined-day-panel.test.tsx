import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMockBillExit } from '@/tests/mocks/data/finances';
import { createMockRentCalendarItem } from '@/tests/mocks/data/rent-calendar';
import { CombinedDayPanel } from '../combined-day-panel';
import type { RentCalendarItem } from '@/lib/api/hooks/use-rent-calendar';
import type { CombinedCalendarBillExit } from '@/lib/api/hooks/use-combined-calendar';

function renderPanel(
  props: {
    rentItems?: RentCalendarItem[];
    billItems?: CombinedCalendarBillExit[];
    isAdmin?: boolean;
  } = {},
) {
  const onPayBill = vi.fn();
  render(
    <CombinedDayPanel
      dayLabel="Quarta, 10/06"
      rentItems={props.rentItems ?? []}
      billItems={props.billItems ?? []}
      isAdmin={props.isAdmin ?? true}
      pendingBillId={null}
      onPayBill={onPayBill}
    />,
  );
  return { onPayBill };
}

describe('CombinedDayPanel', () => {
  it('renders rent entries read-only (no toggle) and bill exits with a toggle', () => {
    renderPanel({
      rentItems: [createMockRentCalendarItem({ tenant_name: 'João Silva' })],
      billItems: [createMockBillExit({ description: 'Conta de Luz' })],
      isAdmin: true,
    });

    expect(screen.getByText('Aluguéis (entradas)')).toBeInTheDocument();
    expect(screen.getByText('João Silva')).toBeInTheDocument();
    expect(screen.getByText('Contas a pagar (saídas)')).toBeInTheDocument();
    expect(screen.getByText('Conta de Luz')).toBeInTheDocument();
    // Exactly one switch: the bill exit (rent entries are read-only).
    expect(screen.getAllByRole('switch')).toHaveLength(1);
  });

  it('calls onPayBill when the bill toggle is used (admin)', async () => {
    const { onPayBill } = renderPanel({
      billItems: [createMockBillExit({ bill_id: 42 })],
      isAdmin: true,
    });
    await userEvent.click(screen.getByRole('switch'));
    expect(onPayBill).toHaveBeenCalledWith(42);
  });

  it('hides the toggle for non-admin users', () => {
    renderPanel({ billItems: [createMockBillExit({ bill_id: 42 })], isAdmin: false });
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
    // Status is still shown (read), via the chip label.
    expect(screen.getByText('Em aberto')).toBeInTheDocument();
  });

  it('shows Portuguese empty states per section', () => {
    renderPanel({ rentItems: [], billItems: [] });
    expect(screen.getByText('Nenhum aluguel neste dia')).toBeInTheDocument();
    expect(screen.getByText('Nenhuma conta a pagar neste dia')).toBeInTheDocument();
  });

  it('formats currency (split + formatCurrency) for entries and exits', () => {
    renderPanel({
      rentItems: [createMockRentCalendarItem({ rental_value: '1500.00' })],
      billItems: [createMockBillExit({ amount_remaining: '350.00' })],
    });
    expect(screen.getByText('+ R$ 1.500,00')).toBeInTheDocument();
    expect(screen.getByText('− R$ 350,00')).toBeInTheDocument();
  });
});
