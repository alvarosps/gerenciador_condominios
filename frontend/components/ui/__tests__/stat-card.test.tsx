import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { StatCard } from '../stat-card';
import { DollarSign } from 'lucide-react';

describe('StatCard', () => {
  it('renders the label and value', () => {
    renderWithProviders(<StatCard label="Caixa" value="R$ 15.000,00" />);
    expect(screen.getByText('Caixa')).toBeInTheDocument();
    expect(screen.getByText('R$ 15.000,00')).toBeInTheDocument();
  });

  it('renders the icon when provided', () => {
    renderWithProviders(
      <StatCard label="Reserva" value="R$ 5.000,00" icon={<DollarSign data-testid="icon" />} />,
    );
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('renders the subLabel when provided', () => {
    renderWithProviders(
      <StatCard label="Atrasados" value="R$ 300,00" subLabel="2 faturas em atraso" />,
    );
    expect(screen.getByText('2 faturas em atraso')).toBeInTheDocument();
  });

  it('applies success tone class to value', () => {
    const { container } = renderWithProviders(
      <StatCard label="Saldo" value="R$ 1.000,00" tone="success" />,
    );
    const valueEl = container.querySelector('.text-success');
    expect(valueEl).toBeInTheDocument();
  });

  it('applies destructive tone class to value', () => {
    const { container } = renderWithProviders(
      <StatCard label="Dívida" value="R$ 500,00" tone="destructive" />,
    );
    const valueEl = container.querySelector('.text-destructive');
    expect(valueEl).toBeInTheDocument();
  });

  it('renders without icon or subLabel', () => {
    renderWithProviders(<StatCard label="Resultado" value="R$ 2.000,00" />);
    expect(screen.getByText('Resultado')).toBeInTheDocument();
    expect(screen.getByText('R$ 2.000,00')).toBeInTheDocument();
  });
});
