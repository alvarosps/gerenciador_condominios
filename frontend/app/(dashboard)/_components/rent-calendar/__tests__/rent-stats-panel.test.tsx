import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RentStatsPanel } from '../rent-stats-panel';
import { formatMonthYear } from '@/lib/utils/formatters';
import type { RentCalendarStats } from '@/lib/api/hooks/use-rent-calendar';

function makeStats(overrides: Partial<RentCalendarStats>): RentCalendarStats {
  return {
    received_total: '4950.00',
    to_receive_total: '9650.00',
    expected_total: '14600.00',
    paid_count: 3,
    due_count: 9,
    overdue_count: 2,
    overdue_total_fee: '37.50',
    vacant_kitnets_count: 2,
    vacant_kitnets_value: '1600.00',
    ...overrides,
  };
}

describe('RentStatsPanel', () => {
  it('renders the month label using the exact formatMonthYear output', () => {
    render(<RentStatsPanel stats={makeStats({})} year={2026} month={6} />);
    expect(screen.getByText(formatMonthYear(2026, 6))).toBeInTheDocument();
  });

  it('renders the received card with count of paid leases', () => {
    render(<RentStatsPanel stats={makeStats({})} year={2026} month={6} />);
    expect(screen.getByText('R$ 4.950,00')).toBeInTheDocument();
    expect(screen.getByText('3 de 9 aluguéis pagos')).toBeInTheDocument();
  });

  it('renders the to-receive card with overdue segment when overdue_count > 0', () => {
    render(<RentStatsPanel stats={makeStats({})} year={2026} month={6} />);
    expect(screen.getByText('R$ 9.650,00')).toBeInTheDocument();
    expect(screen.getByText(/6 pendentes/)).toBeInTheDocument();
    expect(screen.getByText(/2 em atraso/)).toBeInTheDocument();
    expect(screen.getByText(/\+R\$ 37,50 multa/)).toBeInTheDocument();
  });

  it('omits the overdue segment when overdue_count is 0', () => {
    render(
      <RentStatsPanel
        stats={makeStats({ overdue_count: 0, overdue_total_fee: '0.00' })}
        year={2026}
        month={6}
      />,
    );
    expect(screen.queryByText(/em atraso/)).not.toBeInTheDocument();
  });

  it('renders the vacant kitnets card with count and potential value', () => {
    render(<RentStatsPanel stats={makeStats({})} year={2026} month={6} />);
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('R$ 1.600,00')).toBeInTheDocument();
    expect(screen.getByText(/Potencial:/)).toBeInTheDocument();
    expect(screen.getByText(/\/mês/)).toBeInTheDocument();
  });
});
