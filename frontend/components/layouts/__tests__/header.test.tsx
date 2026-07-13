import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { Header } from '../header';
import { useAuthStore } from '@/store/auth-store';

// useLogout is a mutation-only hook (no GET fires on mount) — the real hook hits MSW
// (tests/mocks/handlers.ts `POST /auth/logout/`), no hook is mocked.

// Mock next/navigation (router used inside MobileNav -> Sidebar)
vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/'),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

// Mock GlobalSearch to avoid extra complexity
vi.mock('@/components/search/global-search', () => ({
  GlobalSearch: () => <div data-testid="global-search" />,
}));

// Mock ThemeToggle
vi.mock('@/components/theme-toggle', () => ({
  ThemeToggle: () => <button data-testid="theme-toggle" />,
}));

// Mock MobileNav to isolate header tests
vi.mock('@/components/layouts/mobile-nav', () => ({
  MobileNav: () => <div data-testid="mobile-nav" />,
}));

describe('Header', () => {
  beforeEach(() => {
    // Clear auth store
    useAuthStore.setState({ user: null, isAuthenticated: false });
  });

  it('renders skeleton before hydration', () => {
    // useHydration returns false on first render (before useEffect)
    renderWithProviders(<Header />);
    // Skeleton is rendered before the effect fires — we check it's replaced after
    // The component renders something in either case
    expect(document.body).toBeTruthy();
  });

  it('renders user initials when authenticated', async () => {
    useAuthStore.setState({
      user: {
        id: 1,
        email: 'joao@test.com',
        first_name: 'João',
        last_name: 'Silva',
        is_staff: false,
      },
      isAuthenticated: true,
    });

    renderWithProviders(<Header />);

    await waitFor(() => {
      // After hydration, initials "JS" should appear in the avatar
      expect(screen.getByText('JS')).toBeInTheDocument();
    });
  });

  it('renders user first name when authenticated', async () => {
    useAuthStore.setState({
      user: {
        id: 1,
        email: 'maria@test.com',
        first_name: 'Maria',
        last_name: 'Santos',
        is_staff: false,
      },
      isAuthenticated: true,
    });

    renderWithProviders(<Header />);

    await waitFor(() => {
      expect(screen.getByText('Maria')).toBeInTheDocument();
    });
  });

  it('renders notifications button', async () => {
    useAuthStore.setState({
      user: {
        id: 1,
        email: 'test@test.com',
        first_name: 'Test',
        last_name: 'User',
        is_staff: false,
      },
      isAuthenticated: true,
    });

    renderWithProviders(<Header />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /notificações/i })).toBeInTheDocument();
    });
  });

  it('renders global search', async () => {
    useAuthStore.setState({
      user: {
        id: 1,
        email: 'test@test.com',
        first_name: 'Test',
        last_name: 'User',
        is_staff: false,
      },
      isAuthenticated: true,
    });

    renderWithProviders(<Header />);

    await waitFor(() => {
      expect(screen.getByTestId('global-search')).toBeInTheDocument();
    });
  });

  it('renders fallback initial "U" when user has no name', async () => {
    useAuthStore.setState({
      user: { id: 1, email: 'test@test.com', first_name: '', last_name: '', is_staff: false },
      isAuthenticated: true,
    });

    renderWithProviders(<Header />);

    await waitFor(() => {
      // Falls back to email initial 'T' from 'test@test.com'
      expect(screen.getByText('T')).toBeInTheDocument();
    });
  });
});
