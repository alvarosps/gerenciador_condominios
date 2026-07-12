import { describe, it, expect } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { TenantLeaseModal } from '../tenant-lease-modal';
import type { Tenant } from '@/lib/schemas/tenant.schema';

// useAvailableApartments fires a real GET on mount, served by the global apartments MSW handler
// (tests/mocks/data/apartments.ts) — no hook is mocked. Every test awaits the dialog title (a
// findBy*) before further sync assertions, so the initial fetch settles inside act().

const mockTenant: Tenant = {
  id: 1,
  name: 'Maria Souza',
  cpf_cnpj: '98765432100',
  phone: '(11) 99999-0000',
  email: 'maria@example.com',
  profession: 'Professora',
  marital_status: 'Solteiro(a)',
  due_day: 10,
  dependents: [],
  is_company: false,
  furnitures: [],
};

describe('TenantLeaseModal', () => {
  const defaultProps = {
    mode: 'create' as const,
    tenant: mockTenant,
    open: true,
    onClose: () => undefined,
  };

  it('renders dialog when open', async () => {
    const { queryClient } = renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('does not render dialog when closed', async () => {
    const { queryClient } = renderWithProviders(
      <TenantLeaseModal {...defaultProps} open={false} />
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('shows tenant name in title for create mode', async () => {
    const { queryClient } = renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(await screen.findByText(`Criar Contrato — ${mockTenant.name}`)).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('shows tenant name in title for transfer mode', async () => {
    const { queryClient } = renderWithProviders(
      <TenantLeaseModal {...defaultProps} mode="transfer" />
    );
    expect(await screen.findByText(`Trocar de Kitnet — ${mockTenant.name}`)).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('displays tenant information card', async () => {
    const { queryClient } = renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(await screen.findByText(mockTenant.name)).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders apartment select field', async () => {
    const { queryClient } = renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(await screen.findByText('Apartamento Disponível')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders period and value fields', async () => {
    const { queryClient } = renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(await screen.findByText('Data de Início')).toBeInTheDocument();
    expect(screen.getByText('Validade (meses)')).toBeInTheDocument();
    expect(screen.getByText('Taxa de Tag')).toBeInTheDocument();
    expect(screen.getByText('Valor do Aluguel')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders payment confirmation checkboxes', async () => {
    const { queryClient } = renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(await screen.findByText('Taxa de Limpeza Paga')).toBeInTheDocument();
    expect(screen.getByText('Taxa de Tag Paga')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('shows "Criar Contrato" submit button in create mode', async () => {
    const { queryClient } = renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(await screen.findByRole('button', { name: /criar contrato/i })).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('shows "Transferir" submit button in transfer mode', async () => {
    const { queryClient } = renderWithProviders(
      <TenantLeaseModal {...defaultProps} mode="transfer" />
    );
    expect(await screen.findByRole('button', { name: /transferir/i })).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders cancel button', async () => {
    const { queryClient } = renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(await screen.findByRole('button', { name: /cancelar/i })).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('calls onClose when cancel button is clicked', async () => {
    let closed = false;
    const onClose = () => {
      closed = true;
    };
    const { queryClient } = renderWithProviders(
      <TenantLeaseModal {...defaultProps} onClose={onClose} />
    );
    fireEvent.click(await screen.findByRole('button', { name: /cancelar/i }));
    await waitFor(() => expect(closed).toBe(true));
    await waitForQueriesToSettle(queryClient);
  });
});
