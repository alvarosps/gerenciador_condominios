import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { MainLayout } from '../main-layout';
import { useAuthStore } from '@/store/auth-store';

const replace = vi.fn();

vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/'),
  useRouter: vi.fn(() => ({ replace, push: vi.fn() })),
}));

// Isolate the layout from its heavy chrome (sidebar/header pull in many hooks).
vi.mock('../sidebar', () => ({ Sidebar: () => <div data-testid="sidebar" /> }));
vi.mock('../header', () => ({ Header: () => <div data-testid="header" /> }));
vi.mock('@/components/offline-banner', () => ({ OfflineBanner: () => null }));
vi.mock('@/lib/api/client', () => ({
  apiClient: { get: vi.fn(() => Promise.resolve({ data: null })) },
}));

describe('MainLayout role guard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ user: null, isAuthenticated: false });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('redirects a non-staff user to /tenant', async () => {
    useAuthStore.setState({
      user: { id: 1, email: 't@test.com', first_name: 'Tom', last_name: 'Tenant', is_staff: false },
      isAuthenticated: true,
    });

    renderWithProviders(
      <MainLayout>
        <div data-testid="admin-child">Admin content</div>
      </MainLayout>
    );

    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith('/tenant');
    });
    // The admin shell must not render for a tenant.
    expect(screen.queryByTestId('admin-child')).not.toBeInTheDocument();
  });

  it('renders the dashboard for a staff user', () => {
    useAuthStore.setState({
      user: { id: 2, email: 'a@test.com', first_name: 'Ana', last_name: 'Admin', is_staff: true },
      isAuthenticated: true,
    });

    renderWithProviders(
      <MainLayout>
        <div data-testid="admin-child">Admin content</div>
      </MainLayout>
    );

    expect(screen.getByTestId('admin-child')).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });
});
