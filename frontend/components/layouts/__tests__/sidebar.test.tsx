import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { usePathname } from 'next/navigation';
import { renderWithProviders } from '@/tests/test-utils';
import { useAuthStore } from '@/store/auth-store';
import { Sidebar } from '../sidebar';

vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/'),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(usePathname).mockReturnValue('/');
    useAuthStore.setState({ user: null, isAuthenticated: false });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the app title', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByText('Condomínios Manager')).toBeInTheDocument();
  });

  it('renders main navigation links', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByRole('button', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /prédios/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /apartamentos/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /inquilinos/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /locações/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /móveis/i })).toBeInTheDocument();
  });

  it('renders financial menu item', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByRole('button', { name: /financeiro/i })).toBeInTheDocument();
  });

  it('renders API documentation link', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByRole('button', { name: /documentação da api/i })).toBeInTheDocument();
  });

  it('renders settings navigation link', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByRole('button', { name: /configurações/i })).toBeInTheDocument();
  });

  it('renders contract template link', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByRole('button', { name: /template de contrato/i })).toBeInTheDocument();
  });

  it('calls onNavigate callback when provided and item clicked', () => {
    const onNavigate = vi.fn();
    renderWithProviders(<Sidebar onNavigate={onNavigate} />);
    screen.getByRole('button', { name: /prédios/i }).click();
    expect(onNavigate).toHaveBeenCalledOnce();
  });

  it('renders the legacy financial group with the "(legado)" suffix', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByRole('button', { name: /financeiro \(legado\)/i })).toBeInTheDocument();
  });

  it('lists "Virada de Mês" under the legacy financial group', () => {
    renderWithProviders(<Sidebar />);
    fireEvent.click(screen.getByRole('button', { name: /financeiro \(legado\)/i }));
    expect(screen.getByRole('button', { name: /virada de mês/i })).toBeInTheDocument();
  });

  it('does not render the "Usuários" item for a non-staff user', () => {
    useAuthStore.setState({
      user: { id: 1, email: 't@test.com', first_name: 'Tom', last_name: 'Tenant', is_staff: false },
      isAuthenticated: true,
    });
    renderWithProviders(<Sidebar />);
    expect(screen.queryByRole('button', { name: /usuários/i })).not.toBeInTheDocument();
  });

  it('renders the "Usuários" item for a staff user', () => {
    useAuthStore.setState({
      user: { id: 2, email: 'a@test.com', first_name: 'Ana', last_name: 'Admin', is_staff: true },
      isAuthenticated: true,
    });
    renderWithProviders(<Sidebar />);
    expect(screen.getByRole('button', { name: /usuários/i })).toBeInTheDocument();
  });

  it('auto-expands the group that owns the active route', () => {
    vi.mocked(usePathname).mockReturnValue('/finances/bills');
    renderWithProviders(<Sidebar />);
    // "Contas" is a child of the "Condomínio" group — visible without any click.
    expect(screen.getByRole('button', { name: /^contas$/i })).toBeInTheDocument();
  });

  it('keeps inactive groups collapsed by default', () => {
    vi.mocked(usePathname).mockReturnValue('/finances/bills');
    renderWithProviders(<Sidebar />);
    // "Virada de Mês" (child of the legacy financial group) stays hidden since that group has no active child.
    expect(screen.queryByRole('button', { name: /virada de mês/i })).not.toBeInTheDocument();
  });

  it('renderiza "Contas cadastradas" no grupo Condomínio e marca ativo em /finances/accounts', () => {
    vi.mocked(usePathname).mockReturnValue('/finances/accounts');
    renderWithProviders(<Sidebar />);
    // The group auto-expands because it owns the active route (same pattern as :95-100).
    const item = screen.getByRole('button', { name: /contas cadastradas/i });
    expect(item).toBeInTheDocument();
    expect(item.className).toContain('text-primary');
  });
});
