import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { usePathname } from 'next/navigation';
import { renderWithProviders } from '@/tests/test-utils';
import { useAuthStore } from '@/store/auth-store';
import { MobileNav } from '../mobile-nav';

vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/'),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

describe('MobileNav', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(usePathname).mockReturnValue('/');
    useAuthStore.setState({ user: null, isAuthenticated: false });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('opens the sheet and keeps it open when a group toggle is clicked', () => {
    renderWithProviders(<MobileNav />);
    fireEvent.click(screen.getByRole('button', { name: /abrir menu de navegação/i }));

    const groupToggle = screen.getByRole('button', { name: /condomínio/i });
    fireEvent.click(groupToggle);

    // The group expanding must not close the Sheet — its content (a child link) stays visible.
    expect(screen.getByRole('button', { name: /^contas$/i })).toBeInTheDocument();
  });

  it('closes the sheet when a leaf navigation item is clicked', () => {
    renderWithProviders(<MobileNav />);
    fireEvent.click(screen.getByRole('button', { name: /abrir menu de navegação/i }));

    expect(screen.getByRole('button', { name: /prédios/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /prédios/i }));

    expect(screen.queryByRole('button', { name: /prédios/i })).not.toBeInTheDocument();
  });
});
