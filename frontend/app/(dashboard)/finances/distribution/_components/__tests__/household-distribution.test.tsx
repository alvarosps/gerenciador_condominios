import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HouseholdDistribution } from '../household-distribution';
import type { OwnerHousehold } from '@/lib/api/hooks/use-owner-distribution';

function makeHousehold(overrides: Partial<OwnerHousehold> = {}): OwnerHousehold {
  return {
    name: 'Raul & Célia',
    result_of_month: '600.00',
    carried_in: '-50.00',
    available: '550.00',
    carried_out: '0.00',
    ...overrides,
  };
}

describe('HouseholdDistribution', () => {
  it('renders the four household cards with PT labels and currency values', () => {
    render(<HouseholdDistribution household={makeHousehold()} year={2026} month={7} />);
    expect(screen.getByText(/Resultado do mês/)).toBeInTheDocument();
    expect(screen.getByText('Carregado do mês anterior')).toBeInTheDocument();
    expect(screen.getByText('Disponível para distribuição')).toBeInTheDocument();
    expect(screen.getByText('A carregar para o próximo mês')).toBeInTheDocument();
    expect(screen.getByText('R$ 600,00')).toBeInTheDocument();
    expect(screen.getByText('R$ 550,00')).toBeInTheDocument();
  });

  it('displays available exactly as the backend sent it (no recompute, §4.7)', () => {
    render(
      <HouseholdDistribution
        household={makeHousehold({
          result_of_month: '100.00',
          carried_in: '-30.00',
          available: '70.00',
          carried_out: '0.00',
        })}
        year={2026}
        month={7}
      />,
    );
    expect(screen.getByText('R$ 70,00')).toBeInTheDocument(); // read, not recomputed locally
  });

  it('reads a negative carried_out without recomputing', () => {
    render(
      <HouseholdDistribution
        household={makeHousehold({
          result_of_month: '-50.00',
          carried_in: '-10.00',
          available: '0.00',
          carried_out: '-60.00',
        })}
        year={2026}
        month={7}
      />,
    );
    expect(screen.getByText('-R$ 60,00')).toBeInTheDocument();
  });

  it('colors result_of_month by sign', () => {
    const { rerender } = render(
      <HouseholdDistribution household={makeHousehold({ result_of_month: '600.00' })} year={2026} month={7} />,
    );
    expect(screen.getByText('R$ 600,00').className).toContain('text-success');
    rerender(
      <HouseholdDistribution
        household={makeHousehold({
          result_of_month: '-700.00',
          carried_in: '0.00',
          available: '0.00',
          carried_out: '-650.00',
        })}
        year={2026}
        month={7}
      />,
    );
    expect(screen.getByText('-R$ 700,00').className).toContain('text-destructive');
  });

  it('formats centavos without off-by-cent', () => {
    render(
      <HouseholdDistribution
        household={makeHousehold({ result_of_month: '100.10', available: '100.10' })}
        year={2026}
        month={7}
      />,
    );
    expect(screen.getAllByText('R$ 100,10').length).toBeGreaterThan(0);
  });
});
