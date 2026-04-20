import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { TenantLeaseModal } from '../tenant-lease-modal';
import * as leaseHooks from '@/lib/api/hooks/use-leases';
import * as apartmentHooks from '@/lib/api/hooks/use-apartments';
import type { Tenant } from '@/lib/schemas/tenant.schema';

vi.mock('@/lib/api/hooks/use-leases', async (importOriginal) => {
  const actual = await importOriginal<typeof leaseHooks>();
  return {
    ...actual,
    useCreateLease: vi.fn(),
    useTransferLease: vi.fn(),
  };
});

vi.mock('@/lib/api/hooks/use-apartments', async (importOriginal) => {
  const actual = await importOriginal<typeof apartmentHooks>();
  return {
    ...actual,
    useAvailableApartments: vi.fn(),
  };
});

const idleMutation = { mutateAsync: vi.fn(), isPending: false, mutate: vi.fn() };

function mockHooks() {
  vi.mocked(leaseHooks.useCreateLease).mockReturnValue(idleMutation as never);
  vi.mocked(leaseHooks.useTransferLease).mockReturnValue(idleMutation as never);
  vi.mocked(apartmentHooks.useAvailableApartments).mockReturnValue({
    data: [
      {
        id: 2,
        number: 202,
        rental_value: 1500,
        rental_value_double: null,
        cleaning_fee: 250,
        max_tenants: 1,
        is_rented: false,
        building: { id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores' },
        furnitures: [],
      },
    ],
    isLoading: false,
  } as never);
}

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
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockHooks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders dialog when open', () => {
    renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('does not render dialog when closed', () => {
    renderWithProviders(<TenantLeaseModal {...defaultProps} open={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows tenant name in title for create mode', () => {
    renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(screen.getByText(`Criar Contrato — ${mockTenant.name}`)).toBeInTheDocument();
  });

  it('shows tenant name in title for transfer mode', () => {
    renderWithProviders(<TenantLeaseModal {...defaultProps} mode="transfer" />);
    expect(screen.getByText(`Trocar de Kitnet — ${mockTenant.name}`)).toBeInTheDocument();
  });

  it('displays tenant information card', () => {
    renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(screen.getByText(mockTenant.name)).toBeInTheDocument();
  });

  it('renders apartment select field', () => {
    renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(screen.getByText('Apartamento Disponível')).toBeInTheDocument();
  });

  it('renders period and value fields', () => {
    renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(screen.getByText('Data de Início')).toBeInTheDocument();
    expect(screen.getByText('Validade (meses)')).toBeInTheDocument();
    expect(screen.getByText('Taxa de Tag')).toBeInTheDocument();
    expect(screen.getByText('Valor do Aluguel')).toBeInTheDocument();
  });

  it('renders payment confirmation checkboxes', () => {
    renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(screen.getByText('Taxa de Limpeza Paga')).toBeInTheDocument();
    expect(screen.getByText('Depósito de Tag Pago')).toBeInTheDocument();
  });

  it('shows "Criar Contrato" submit button in create mode', () => {
    renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: /criar contrato/i })).toBeInTheDocument();
  });

  it('shows "Transferir" submit button in transfer mode', () => {
    renderWithProviders(<TenantLeaseModal {...defaultProps} mode="transfer" />);
    expect(screen.getByRole('button', { name: /transferir/i })).toBeInTheDocument();
  });

  it('renders cancel button', () => {
    renderWithProviders(<TenantLeaseModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn();
    renderWithProviders(<TenantLeaseModal {...defaultProps} onClose={onClose} />);
    screen.getByRole('button', { name: /cancelar/i }).click();
    expect(onClose).toHaveBeenCalledOnce();
  });
});
