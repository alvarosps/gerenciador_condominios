import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { RentMonthGrid } from '../rent-month-grid';
import type { RentCalendarDay, RentCalendarItem } from '@/lib/api/hooks/use-rent-calendar';

function makeItem(overrides: Partial<RentCalendarItem>): RentCalendarItem {
  return {
    lease_id: 1,
    tenant_name: 'João Silva',
    apartment_number: 101,
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
  year: 2026,
  month: 6,
  today: '2026-06-15',
  selectedDay: 15,
  onSelectDay: vi.fn(),
  onPrevMonth: vi.fn(),
  onNextMonth: vi.fn(),
};

describe('RentMonthGrid', () => {
  it('renders one cell per day for the given month (June 2026 = 30 days)', () => {
    render(<RentMonthGrid {...baseProps} days={[]} />);
    const grid = screen.getByRole('grid');
    const dayCells = within(grid).getAllByRole('gridcell');
    // 30 day cells (empty leading-offset placeholders are not gridcells)
    expect(dayCells).toHaveLength(30);
    expect(within(grid).getByText('1')).toBeInTheDocument();
    expect(within(grid).getByText('30')).toBeInTheDocument();
  });

  it('renders tenant chips on days that have items', () => {
    const days: RentCalendarDay[] = [
      { day: 5, date: '2026-06-05', weekday: 'Sexta', items: [makeItem({})] },
    ];
    render(<RentMonthGrid {...baseProps} days={days} />);
    expect(screen.getByText('João Silva')).toBeInTheDocument();
  });

  it('calls onSelectDay with the clicked day number', () => {
    const onSelectDay = vi.fn();
    render(<RentMonthGrid {...baseProps} days={[]} onSelectDay={onSelectDay} />);
    fireEvent.click(screen.getByRole('gridcell', { name: 'Dia 12' }));
    expect(onSelectDay).toHaveBeenCalledWith(12);
  });

  it('marks today and the selected day with accessible labels', () => {
    render(<RentMonthGrid {...baseProps} days={[]} selectedDay={10} />);
    expect(screen.getByRole('gridcell', { name: 'Dia 15 (hoje)' })).toBeInTheDocument();
    expect(screen.getByRole('gridcell', { name: 'Dia 10', selected: true })).toBeInTheDocument();
  });

  it('shows the tenant on the clamped day (due day 31 -> day 30)', () => {
    const days: RentCalendarDay[] = [
      { day: 30, date: '2026-06-30', weekday: 'Terça', items: [makeItem({ tenant_name: 'Teresa Gomes' })] },
    ];
    render(<RentMonthGrid {...baseProps} days={days} />);
    const cell = screen.getByRole('gridcell', { name: 'Dia 30' });
    expect(within(cell).getByText('Teresa Gomes')).toBeInTheDocument();
  });

  it('fires month navigation callbacks', () => {
    const onPrevMonth = vi.fn();
    const onNextMonth = vi.fn();
    render(
      <RentMonthGrid {...baseProps} days={[]} onPrevMonth={onPrevMonth} onNextMonth={onNextMonth} />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Mês anterior' }));
    fireEvent.click(screen.getByRole('button', { name: 'Próximo mês' }));
    expect(onPrevMonth).toHaveBeenCalledTimes(1);
    expect(onNextMonth).toHaveBeenCalledTimes(1);
  });
});
