import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMockBillExit, createMockCombinedCalendar } from '@/tests/mocks/data/finances';
import { CombinedMonthGrid } from '../combined-month-grid';
import type { CombinedCalendarDay } from '@/lib/api/hooks/use-combined-calendar';

function renderGrid(days: CombinedCalendarDay[], overrides: { selectedDay?: number } = {}) {
  const onSelectDay = vi.fn();
  render(
    <CombinedMonthGrid
      year={2026}
      month={6}
      days={days}
      today="2026-06-07"
      selectedDay={overrides.selectedDay ?? 7}
      onSelectDay={onSelectDay}
      onPrevMonth={vi.fn()}
      onNextMonth={vi.fn()}
    />,
  );
  return { onSelectDay };
}

describe('CombinedMonthGrid', () => {
  it('renders 30 day cells for June 2026 with the leading offset', () => {
    renderGrid([]);
    const cells = screen.getAllByRole('gridcell');
    expect(cells).toHaveLength(30);
    // June 1 2026 is a Monday → one leading offset cell (Sunday) before day 1.
    const firstCell = screen.getByRole('gridcell', { name: /^Dia 1$/i });
    expect(within(firstCell).getByText('1')).toBeInTheDocument();
  });

  it('shows distinguishable chips (label) for days with entries and exits', () => {
    const calendar = createMockCombinedCalendar({
      days: [
        {
          day: 10,
          date: '2026-06-10',
          weekday: 'Quarta',
          rent_entries: [],
          bill_exits: [createMockBillExit({ description: 'Conta de Luz' })],
        },
      ],
    });
    renderGrid(calendar.days);
    expect(screen.getByText('Conta de Luz')).toBeInTheDocument();
    // Legend distinguishes entries vs exits by label, not color alone.
    expect(screen.getByText('Saídas (contas)')).toBeInTheDocument();
    expect(screen.getByText('Entradas (aluguéis)')).toBeInTheDocument();
  });

  it('calls onSelectDay when a cell is clicked', async () => {
    const { onSelectDay } = renderGrid([]);
    await userEvent.click(screen.getByRole('gridcell', { name: /^Dia 10$/i }));
    expect(onSelectDay).toHaveBeenCalledWith(10);
  });

  it('highlights today and the selected day via accessible labels (not color only)', () => {
    renderGrid([], { selectedDay: 7 });
    expect(screen.getByRole('gridcell', { name: /Dia 7 \(hoje\)/i })).toBeInTheDocument();
    const selected = screen.getByRole('gridcell', { name: /Dia 7/i });
    expect(selected).toHaveAttribute('aria-selected', 'true');
  });
});
