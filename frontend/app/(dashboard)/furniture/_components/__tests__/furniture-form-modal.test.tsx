import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { FurnitureFormModal } from '../furniture-form-modal';
import * as furnitureHooks from '@/lib/api/hooks/use-furniture';

vi.mock('@/lib/api/hooks/use-furniture', async (importOriginal) => {
  const actual = await importOriginal<typeof furnitureHooks>();
  return {
    ...actual,
    useCreateFurniture: vi.fn(),
    useUpdateFurniture: vi.fn(),
  };
});

const idleMutation = { mutateAsync: vi.fn(), isPending: false };

function mockHooks() {
  vi.mocked(furnitureHooks.useCreateFurniture).mockReturnValue(idleMutation as never);
  vi.mocked(furnitureHooks.useUpdateFurniture).mockReturnValue(idleMutation as never);
}

describe('FurnitureFormModal', () => {
  const defaultProps = { open: true, onClose: vi.fn() };

  beforeEach(() => {
    vi.clearAllMocks();
    mockHooks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders dialog when open', () => {
    renderWithProviders(<FurnitureFormModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('does not render dialog when closed', () => {
    renderWithProviders(<FurnitureFormModal {...defaultProps} open={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows "Novo Móvel" title when creating', () => {
    renderWithProviders(<FurnitureFormModal {...defaultProps} />);
    expect(screen.getByText('Novo Móvel')).toBeInTheDocument();
  });

  it('shows "Editar Móvel" title when editing', () => {
    const furniture = { id: 1, name: 'Sofá' };
    renderWithProviders(<FurnitureFormModal {...defaultProps} furniture={furniture as never} />);
    expect(screen.getByText('Editar Móvel')).toBeInTheDocument();
  });

  it('renders name input field', () => {
    renderWithProviders(<FurnitureFormModal {...defaultProps} />);
    expect(screen.getByText('Nome do Móvel *')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ex: Sofá, Cama, Mesa')).toBeInTheDocument();
  });

  it('renders cancel and submit buttons', () => {
    renderWithProviders(<FurnitureFormModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /criar/i })).toBeInTheDocument();
  });

  it('shows "Atualizar" button when editing', () => {
    const furniture = { id: 1, name: 'Sofá' };
    renderWithProviders(<FurnitureFormModal {...defaultProps} furniture={furniture as never} />);
    expect(screen.getByRole('button', { name: /atualizar/i })).toBeInTheDocument();
  });

  it('pre-fills name field when editing', () => {
    const furniture = { id: 1, name: 'Sofá de Couro' };
    renderWithProviders(<FurnitureFormModal {...defaultProps} furniture={furniture as never} />);
    expect(screen.getByDisplayValue('Sofá de Couro')).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn();
    renderWithProviders(<FurnitureFormModal open={true} onClose={onClose} />);
    screen.getByRole('button', { name: /cancelar/i }).click();
    expect(onClose).toHaveBeenCalledOnce();
  });
});
