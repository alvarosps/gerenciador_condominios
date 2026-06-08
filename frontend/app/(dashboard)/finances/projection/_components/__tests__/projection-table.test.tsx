import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { ProjectionTable } from '../projection-table';
import type { CondoProjectionMonth } from '@/lib/api/hooks/use-condo-projection';

function makeMonth(overrides: Partial<CondoProjectionMonth> = {}): CondoProjectionMonth {
  return {
    year: 2026,
    month: 7,
    income_total: '4000.00',
    expenses_total: '3200.00',
    net: '800.00',
    cumulative_cash: '5800.00',
    is_actual: true,
    is_closed: false,
    ...overrides,
  };
}

describe('ProjectionTable', () => {
  it('renders a Real badge for actual months and Projetado for future months', () => {
    render(
      <ProjectionTable
        months={[
          makeMonth({ month: 7, is_actual: true }),
          makeMonth({ month: 8, is_actual: false }),
        ]}
      />,
    );
    expect(screen.getByText('Real')).toBeInTheDocument();
    expect(screen.getByText('Projetado')).toBeInTheDocument();
  });

  it('shows each month cumulative_cash in the Acumulado column', () => {
    render(
      <ProjectionTable
        months={[
          makeMonth({ month: 7, cumulative_cash: '5800.00' }),
          makeMonth({ month: 8, cumulative_cash: '6600.00', is_actual: false }),
        ]}
      />,
    );
    // The first month's cumulative shows in the body (the footer shows only the last = 6600).
    expect(screen.getByText('R$ 5.800,00')).toBeInTheDocument();
  });

  it('colors the result by sign (negative = destructive, positive = success)', () => {
    render(
      <ProjectionTable
        months={[
          makeMonth({ month: 7, net: '800.00' }),
          makeMonth({ month: 8, net: '-500.00', is_actual: false }),
        ]}
      />,
    );
    const positive = screen.getByText('R$ 800,00');
    const negative = screen.getByText('-R$ 500,00');
    expect(positive.className).toContain('text-success');
    expect(negative.className).toContain('text-destructive');
  });

  it('footer sums income/expense but shows the LAST cumulative_cash (not the column sum)', () => {
    render(
      <ProjectionTable
        months={[
          makeMonth({ month: 7, income_total: '4000.00', expenses_total: '3200.00', cumulative_cash: '5800.00' }),
          makeMonth({ month: 8, income_total: '4000.00', expenses_total: '3200.00', cumulative_cash: '6600.00', is_actual: false }),
        ]}
      />,
    );
    const footer = screen.getByText('Total').closest('tr');
    expect(footer).not.toBeNull();
    const footerScope = within(footer as HTMLElement);
    // Σ income = 8000, Σ expense = 6400, final cumulative = 6600 (last), NOT 12400 (column sum).
    expect(footerScope.getByText('R$ 8.000,00')).toBeInTheDocument();
    expect(footerScope.getByText('R$ 6.400,00')).toBeInTheDocument();
    expect(footerScope.getByText('R$ 6.600,00')).toBeInTheDocument();
    expect(footerScope.queryByText('R$ 12.400,00')).toBeNull();
  });

  it('sums centavos without off-by-cent (quantized at the boundary)', () => {
    render(
      <ProjectionTable
        months={[
          makeMonth({ month: 7, income_total: '100.10' }),
          makeMonth({ month: 8, income_total: '200.20', is_actual: false }),
          makeMonth({ month: 9, income_total: '300.30', is_actual: false }),
        ]}
      />,
    );
    const footer = screen.getByText('Total').closest('tr');
    expect(within(footer as HTMLElement).getByText('R$ 600,60')).toBeInTheDocument();
  });

  it('renders an empty state without a footer when there are no months', () => {
    render(<ProjectionTable months={[]} />);
    expect(screen.getByText('Nenhum mês para exibir.')).toBeInTheDocument();
    expect(screen.queryByText('Total')).toBeNull();
  });
});
