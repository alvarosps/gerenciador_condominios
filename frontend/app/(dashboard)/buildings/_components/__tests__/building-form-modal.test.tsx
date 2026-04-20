import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { BuildingFormModal } from '../building-form-modal';
import * as buildingHooks from '@/lib/api/hooks/use-buildings';

vi.mock('@/lib/api/hooks/use-buildings', async (importOriginal) => {
  const actual = await importOriginal<typeof buildingHooks>();
  return {
    ...actual,
    useCreateBuilding: vi.fn(),
    useUpdateBuilding: vi.fn(),
  };
});

const idleMutation = { mutateAsync: vi.fn(), isPending: false };

function mockHooks() {
  vi.mocked(buildingHooks.useCreateBuilding).mockReturnValue(idleMutation as never);
  vi.mocked(buildingHooks.useUpdateBuilding).mockReturnValue(idleMutation as never);
}

describe('BuildingFormModal', () => {
  const defaultProps = { open: true, onClose: vi.fn() };

  beforeEach(() => {
    vi.clearAllMocks();
    mockHooks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders dialog when open', () => {
    renderWithProviders(<BuildingFormModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('does not render dialog when closed', () => {
    renderWithProviders(<BuildingFormModal {...defaultProps} open={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows "Novo Prédio" title when creating', () => {
    renderWithProviders(<BuildingFormModal {...defaultProps} />);
    expect(screen.getByText('Novo Prédio')).toBeInTheDocument();
  });

  it('shows "Editar Prédio" title when editing', () => {
    const building = { id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores, 836' };
    renderWithProviders(<BuildingFormModal {...defaultProps} building={building as never} />);
    expect(screen.getByText('Editar Prédio')).toBeInTheDocument();
  });

  it('renders all required form fields', () => {
    renderWithProviders(<BuildingFormModal {...defaultProps} />);
    expect(screen.getByText('Número da Rua *')).toBeInTheDocument();
    expect(screen.getByText('Nome do Prédio *')).toBeInTheDocument();
    expect(screen.getByText('Endereço Completo *')).toBeInTheDocument();
  });

  it('renders cancel and submit buttons', () => {
    renderWithProviders(<BuildingFormModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /criar/i })).toBeInTheDocument();
  });

  it('shows "Atualizar" button when editing', () => {
    const building = { id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores, 836' };
    renderWithProviders(<BuildingFormModal {...defaultProps} building={building as never} />);
    expect(screen.getByRole('button', { name: /atualizar/i })).toBeInTheDocument();
  });

  it('pre-fills form fields when editing', () => {
    const building = { id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores, 836' };
    renderWithProviders(<BuildingFormModal {...defaultProps} building={building as never} />);
    expect(screen.getByDisplayValue('Prédio Central')).toBeInTheDocument();
    expect(screen.getByDisplayValue('836')).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn();
    renderWithProviders(<BuildingFormModal open={true} onClose={onClose} />);
    screen.getByRole('button', { name: /cancelar/i }).click();
    expect(onClose).toHaveBeenCalledOnce();
  });
});
