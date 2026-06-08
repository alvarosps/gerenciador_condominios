import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ExternalOwnersSection } from '../external-owners-section';
import type { ExternalOwnerEntry } from '@/lib/api/hooks/use-owner-distribution';

const OWNERS: ExternalOwnerEntry[] = [
  { owner_id: 2, owner_name: 'Tiago', leases_count: 2, rent_total: '1600.00' },
  { owner_id: 3, owner_name: 'Alvaro', leases_count: 2, rent_total: '1500.00' },
];

describe('ExternalOwnersSection', () => {
  it('lists each external owner with name and total', () => {
    render(<ExternalOwnersSection externalOwners={OWNERS} externalTotal="3100.00" />);
    expect(screen.getByText('Tiago')).toBeInTheDocument();
    expect(screen.getByText('Alvaro')).toBeInTheDocument();
    expect(screen.getByText('R$ 1.600,00')).toBeInTheDocument();
    expect(screen.getByText('R$ 1.500,00')).toBeInTheDocument();
  });

  it('shows the mandatory display-only PT note', () => {
    render(<ExternalOwnersSection externalOwners={OWNERS} externalTotal="3100.00" />);
    expect(screen.getByText(/não entra no resultado do condomínio/)).toBeInTheDocument();
  });

  it('renders an empty state with no totals when there are no external owners', () => {
    render(<ExternalOwnersSection externalOwners={[]} externalTotal="0.00" />);
    expect(screen.getByText('Nenhum dono externo neste mês.')).toBeInTheDocument();
    expect(screen.queryByText(/Total dos donos externos/)).toBeNull();
  });

  it('shows the external total as a clearly separate, owner-only figure', () => {
    render(<ExternalOwnersSection externalOwners={OWNERS} externalTotal="3100.00" />);
    expect(screen.getByText(/Total dos donos externos/)).toBeInTheDocument();
    expect(screen.getByText(/R\$ 3\.100,00/)).toBeInTheDocument();
  });
});
