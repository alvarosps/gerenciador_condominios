import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { PageHeader } from '../page-header';

describe('PageHeader', () => {
  it('renders the title as an h1 with the standard density classes', () => {
    renderWithProviders(<PageHeader title="Prédios" />);
    const heading = screen.getByRole('heading', { level: 1, name: 'Prédios' });
    expect(heading).toHaveClass('text-2xl', 'font-bold', 'tracking-tight');
  });

  it('renders the description when provided', () => {
    renderWithProviders(
      <PageHeader title="Prédios" description="Gerencie os prédios do condomínio" />
    );
    expect(screen.getByText('Gerencie os prédios do condomínio')).toBeInTheDocument();
  });

  it('omits the description paragraph when not provided', () => {
    const { container } = renderWithProviders(<PageHeader title="Prédios" />);
    expect(container.querySelector('p')).toBeNull();
  });

  it('renders actions in the slot when provided', () => {
    renderWithProviders(<PageHeader title="Prédios" actions={<button>Novo Prédio</button>} />);
    expect(screen.getByRole('button', { name: 'Novo Prédio' })).toBeInTheDocument();
  });
});
