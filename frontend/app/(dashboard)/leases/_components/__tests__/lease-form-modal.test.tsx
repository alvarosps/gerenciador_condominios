import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { LeaseFormModal } from '../lease-form-modal';
import * as leaseHooks from '@/lib/api/hooks/use-leases';
import * as apartmentHooks from '@/lib/api/hooks/use-apartments';
import * as tenantHooks from '@/lib/api/hooks/use-tenants';

vi.mock('@/lib/api/hooks/use-leases', async (importOriginal) => {
  const actual = await importOriginal<typeof leaseHooks>();
  return {
    ...actual,
    useCreateLease: vi.fn(),
    useUpdateLease: vi.fn(),
  };
});

vi.mock('@/lib/api/hooks/use-apartments', async (importOriginal) => {
  const actual = await importOriginal<typeof apartmentHooks>();
  return {
    ...actual,
    useAvailableApartments: vi.fn(),
  };
});

vi.mock('@/lib/api/hooks/use-tenants', async (importOriginal) => {
  const actual = await importOriginal<typeof tenantHooks>();
  return { ...actual, useTenants: vi.fn() };
});

const idleMutation = { mutateAsync: vi.fn(), isPending: false };

function mockHooks() {
  vi.mocked(leaseHooks.useCreateLease).mockReturnValue(idleMutation as never);
  vi.mocked(leaseHooks.useUpdateLease).mockReturnValue(idleMutation as never);
  vi.mocked(apartmentHooks.useAvailableApartments).mockReturnValue({
    data: [
      {
        id: 1,
        number: 101,
        rental_value: 1200,
        rental_value_double: null,
        cleaning_fee: 200,
        max_tenants: 1,
        is_rented: false,
        building: { id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores' },
        furnitures: [],
      },
    ],
    isLoading: false,
  } as never);
  vi.mocked(tenantHooks.useTenants).mockReturnValue({
    data: [
      {
        id: 1,
        name: 'João Silva',
        cpf_cnpj: '12345678901',
        due_day: 5,
        dependents: [],
      },
    ],
    isLoading: false,
  } as never);
}

describe('LeaseFormModal', () => {
  const defaultProps = { open: true, onClose: vi.fn() };

  beforeEach(() => {
    vi.clearAllMocks();
    mockHooks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders dialog when open', () => {
    renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('does not render dialog when closed', () => {
    renderWithProviders(<LeaseFormModal {...defaultProps} open={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows "Nova Locação" title when creating', () => {
    renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(screen.getByText('Nova Locação')).toBeInTheDocument();
  });

  it('shows "Editar Locação" title when editing', () => {
    const lease = {
      id: 1,
      apartment: {
        id: 1,
        number: 101,
        rental_value: 1200,
        rental_value_double: null,
        cleaning_fee: 200,
        max_tenants: 1,
        is_rented: true,
        building: { id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores' },
        furnitures: [],
      },
      responsible_tenant: { id: 1, name: 'João Silva', cpf_cnpj: '12345678901', due_day: 5 },
      number_of_tenants: 1,
      rental_value: 1200,
      start_date: '2024-01-01',
      validity_months: 12,
      tag_fee: 50,
      contract_generated: false,
    };
    renderWithProviders(<LeaseFormModal {...defaultProps} lease={lease as never} />);
    expect(screen.getByText('Editar Locação')).toBeInTheDocument();
  });

  it('renders apartment and tenant select fields', () => {
    renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(screen.getByText('Apartamento')).toBeInTheDocument();
    expect(screen.getByText('Inquilino Responsável')).toBeInTheDocument();
  });

  it('renders period and value fields', () => {
    renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(screen.getByText('Data de Início')).toBeInTheDocument();
    expect(screen.getByText('Validade (meses)')).toBeInTheDocument();
    expect(screen.getByText('Taxa de Tag')).toBeInTheDocument();
    expect(screen.getByText('Valor do Aluguel')).toBeInTheDocument();
  });

  it('renders payment confirmation checkboxes', () => {
    renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(screen.getByText('Taxa de Limpeza Paga')).toBeInTheDocument();
    expect(screen.getByText('Depósito de Tag Pago')).toBeInTheDocument();
  });

  it('renders cancel and submit buttons', () => {
    renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /criar/i })).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn();
    renderWithProviders(<LeaseFormModal open={true} onClose={onClose} />);
    screen.getByRole('button', { name: /cancelar/i }).click();
    expect(onClose).toHaveBeenCalledOnce();
  });
});
