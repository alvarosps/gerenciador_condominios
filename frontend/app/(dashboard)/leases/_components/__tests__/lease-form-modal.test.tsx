import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { LeaseFormModal } from '../lease-form-modal';
import * as leaseHooks from '@/lib/api/hooks/use-leases';
import * as apartmentHooks from '@/lib/api/hooks/use-apartments';
import * as tenantHooks from '@/lib/api/hooks/use-tenants';
import * as authStore from '@/store/auth-store';

function submitForm() {
  // Radix Dialog portals its content to document.body, so query via the dialog.
  const form = screen.getByRole('dialog').querySelector('form');
  if (!form) throw new Error('form not found');
  fireEvent.submit(form);
}

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

vi.mock('@/store/auth-store', () => ({ useAuthStore: vi.fn() }));

const createMutateAsync = vi.fn();
const updateMutateAsync = vi.fn();

function setIsStaff(isStaff: boolean) {
  vi.mocked(authStore.useAuthStore).mockReturnValue({ user: { is_staff: isStaff } } as never);
}

function mockHooks() {
  vi.mocked(leaseHooks.useCreateLease).mockReturnValue({
    mutateAsync: createMutateAsync,
    isPending: false,
  } as never);
  vi.mocked(leaseHooks.useUpdateLease).mockReturnValue({
    mutateAsync: updateMutateAsync,
    isPending: false,
  } as never);
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
  setIsStaff(true);
}

const editableLease = {
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
  tag_fee: 20,
  cleaning_fee_paid: false,
  tag_deposit_paid: false,
  contract_generated: false,
  prepaid_until: null as string | null,
  is_salary_offset: false,
};

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
    renderWithProviders(<LeaseFormModal {...defaultProps} lease={editableLease as never} />);
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
    expect(screen.getByText('Taxa de Tag Paga')).toBeInTheDocument();
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

  // --- Session 35: prepaid_until + is_salary_offset (is_staff gated) ---

  it('renders the prepaid/salary-offset fields for admin (is_staff)', () => {
    setIsStaff(true);
    renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(screen.getByText('Aluguel compensado por salário')).toBeInTheDocument();
    expect(screen.getByText('Pré-pago até')).toBeInTheDocument();
  });

  it('hides the prepaid/salary-offset fields for non-admin', () => {
    setIsStaff(false);
    renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(screen.queryByText('Aluguel compensado por salário')).not.toBeInTheDocument();
    expect(screen.queryByText('Pré-pago até')).not.toBeInTheDocument();
  });

  it('pre-fills prepaid_until when editing', () => {
    setIsStaff(true);
    renderWithProviders(
      <LeaseFormModal
        {...defaultProps}
        lease={{ ...editableLease, prepaid_until: '2026-07-01', is_salary_offset: true } as never}
      />,
    );
    expect(screen.getByDisplayValue('2026-07-01')).toBeInTheDocument();
  });

  it('submits prepaid_until and is_salary_offset on update', async () => {
    setIsStaff(true);
    renderWithProviders(
      <LeaseFormModal
        {...defaultProps}
        lease={{ ...editableLease, prepaid_until: '2026-07-01', is_salary_offset: true } as never}
      />,
    );
    submitForm();
    await waitFor(() => expect(updateMutateAsync).toHaveBeenCalled());
    expect(updateMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ prepaid_until: '2026-07-01', is_salary_offset: true }),
    );
  });

  it('clears prepaid_until to null when the date input is emptied', async () => {
    setIsStaff(true);
    renderWithProviders(
      <LeaseFormModal
        {...defaultProps}
        lease={{ ...editableLease, prepaid_until: '2026-07-01' } as never}
      />,
    );
    fireEvent.change(screen.getByDisplayValue('2026-07-01'), { target: { value: '' } });
    submitForm();
    await waitFor(() => expect(updateMutateAsync).toHaveBeenCalled());
    expect(updateMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ prepaid_until: null }),
    );
  });
});
