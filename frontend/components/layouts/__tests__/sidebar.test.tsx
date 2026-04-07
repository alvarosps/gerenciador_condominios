import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { Sidebar } from '../sidebar';

vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/'),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    expect(screen.getByRole('button', { name: /api documentation/i })).toBeInTheDocument();
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
});
