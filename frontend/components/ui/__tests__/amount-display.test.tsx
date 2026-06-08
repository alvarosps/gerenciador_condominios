import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { AmountDisplay } from '../amount-display';

describe('AmountDisplay', () => {
  it('renders a positive number as formatted currency', () => {
    renderWithProviders(<AmountDisplay amount={1500} />);
    expect(screen.getByText(/R\$\s*1\.500,00/)).toBeInTheDocument();
  });

  it('renders a negative number with minus sign', () => {
    renderWithProviders(<AmountDisplay amount={-300} />);
    expect(screen.getByText(/-.*300/)).toBeInTheDocument();
  });

  it('renders a string amount', () => {
    renderWithProviders(<AmountDisplay amount="2000.50" />);
    expect(screen.getByText(/2\.000,50/)).toBeInTheDocument();
  });

  it('shows explicit plus sign when showSign=true and positive', () => {
    renderWithProviders(<AmountDisplay amount={500} showSign />);
    const el = screen.getByText(/\+/);
    expect(el).toBeInTheDocument();
  });

  it('shows minus sign when showSign=true and negative', () => {
    renderWithProviders(<AmountDisplay amount={-200} showSign />);
    const el = screen.getByText(/-/);
    expect(el).toBeInTheDocument();
  });

  it('applies autoTone success class for positive amounts', () => {
    const { container } = renderWithProviders(<AmountDisplay amount={1000} autoTone />);
    expect(container.querySelector('.text-success')).toBeInTheDocument();
  });

  it('applies autoTone destructive class for negative amounts', () => {
    const { container } = renderWithProviders(<AmountDisplay amount={-100} autoTone />);
    expect(container.querySelector('.text-destructive')).toBeInTheDocument();
  });

  it('applies explicit tone class', () => {
    const { container } = renderWithProviders(<AmountDisplay amount={0} tone="warning" />);
    expect(container.querySelector('.text-warning')).toBeInTheDocument();
  });

  it('applies size classes', () => {
    const { container } = renderWithProviders(<AmountDisplay amount={100} size="lg" />);
    expect(container.querySelector('.text-2xl')).toBeInTheDocument();
  });
});
