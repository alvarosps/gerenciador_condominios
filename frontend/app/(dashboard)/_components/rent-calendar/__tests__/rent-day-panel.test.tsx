import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RentDayPanel } from '../rent-day-panel';
import type { RentCalendarItem } from '@/lib/api/hooks/use-rent-calendar';

function makeItem(overrides: Partial<RentCalendarItem>): RentCalendarItem {
  return {
    lease_id: 1,
    tenant_name: 'Ana Lima',
    apartment_number: 102,
    building_number: '836',
    rental_value: '1500.00',
    is_paid: false,
    payment_date: null,
    is_overdue: false,
    day_passed: false,
    can_toggle: true,
    late_fee: '0.00',
    late_days: 0,
    ...overrides,
  };
}

const baseProps = {
  dayLabel: 'Segunda, 15/06',
  nextDueDate: '2026-06-20' as string | null,
  pendingLeaseId: null as number | null,
  onToggle: vi.fn(),
  onGoToday: vi.fn(),
  onGoNextDue: vi.fn(),
};

describe('RentDayPanel', () => {
  it('renders an "A vencer" item with the formatted value', () => {
    render(<RentDayPanel {...baseProps} items={[makeItem({})]} />);
    expect(screen.getByText('A vencer')).toBeInTheDocument();
    expect(screen.getByText('R$ 1.500,00')).toBeInTheDocument();
    expect(screen.getByText('Ana Lima')).toBeInTheDocument();
    expect(screen.getByText('Apto 102 · Préd. 836')).toBeInTheDocument();
  });

  it('renders a paid item with "Pago em DD/MM" and a checked toggle', () => {
    render(
      <RentDayPanel
        {...baseProps}
        items={[makeItem({ is_paid: true, payment_date: '2026-06-15' })]}
      />,
    );
    expect(screen.getByText('Pago em 15/06')).toBeInTheDocument();
    expect(screen.getByRole('switch')).toBeChecked();
  });

  it('disables the toggle for a paid item whose day already passed', () => {
    render(
      <RentDayPanel
        {...baseProps}
        items={[
          makeItem({
            is_paid: true,
            payment_date: '2026-06-10',
            day_passed: true,
            can_toggle: false,
          }),
        ]}
      />,
    );
    expect(screen.getByRole('switch')).toBeDisabled();
  });

  it('disables only the toggle of the lease that is currently pending', () => {
    const { unmount } = render(
      <RentDayPanel {...baseProps} pendingLeaseId={1} items={[makeItem({ lease_id: 1 })]} />,
    );
    expect(screen.getByRole('switch')).toBeDisabled();
    unmount();
    // A different lease (not the pending one) keeps its toggle enabled.
    render(<RentDayPanel {...baseProps} pendingLeaseId={1} items={[makeItem({ lease_id: 2 })]} />);
    expect(screen.getByRole('switch')).not.toBeDisabled();
  });

  it('renders an overdue item with label, late days, and formatted late fee', () => {
    render(
      <RentDayPanel
        {...baseProps}
        items={[
          makeItem({
            is_overdue: true,
            day_passed: true,
            late_fee: '12.50',
            late_days: 5,
          }),
        ]}
      />,
    );
    expect(screen.getByText(/Em atraso/)).toBeInTheDocument();
    expect(screen.getByText(/5 dias/)).toBeInTheDocument();
    expect(screen.getByText(/multa R\$ 12,50/)).toBeInTheDocument();
  });

  it('hides overdue styling and late fee when an overdue item is (optimistically) paid', () => {
    // Regression: during the optimistic flip is_paid becomes true while is_overdue is
    // still stale-true; the card must show the paid style only — no red card, no "+ multa".
    const { container } = render(
      <RentDayPanel
        {...baseProps}
        items={[
          makeItem({
            is_paid: true,
            payment_date: '2026-06-15',
            is_overdue: true,
            day_passed: true,
            late_fee: '12.50',
            late_days: 5,
          }),
        ]}
      />,
    );
    expect(screen.getByText('Pago')).toBeInTheDocument();
    expect(screen.queryByText(/multa/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Em atraso/)).not.toBeInTheDocument();
    expect(container.querySelector('.bg-success\\/10')).toBeInTheDocument();
    expect(container.querySelector('.bg-destructive\\/10')).not.toBeInTheDocument();
  });

  it('renders an empty state when there are no items', () => {
    render(<RentDayPanel {...baseProps} items={[]} />);
    expect(screen.getByText('Nenhum vencimento neste dia')).toBeInTheDocument();
  });

  it('fires onGoToday and onGoNextDue when the buttons are clicked', () => {
    const onGoToday = vi.fn();
    const onGoNextDue = vi.fn();
    render(
      <RentDayPanel
        {...baseProps}
        items={[makeItem({})]}
        onGoToday={onGoToday}
        onGoNextDue={onGoNextDue}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Hoje' }));
    fireEvent.click(screen.getByRole('button', { name: 'Próx. vencimento' }));
    expect(onGoToday).toHaveBeenCalledTimes(1);
    expect(onGoNextDue).toHaveBeenCalledTimes(1);
  });

  it('disables the "Próx. vencimento" button when nextDueDate is null', () => {
    render(<RentDayPanel {...baseProps} items={[makeItem({})]} nextDueDate={null} />);
    expect(screen.getByRole('button', { name: 'Próx. vencimento' })).toBeDisabled();
  });
});
