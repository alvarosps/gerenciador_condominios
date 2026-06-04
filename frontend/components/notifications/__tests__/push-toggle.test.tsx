import { afterEach, describe, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { toast } from 'sonner';
import { PushToggle } from '../push-toggle';
import { renderWithProviders, screen, waitFor, userEvent } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

interface FakePushSubscription {
  endpoint: string;
  unsubscribe: ReturnType<typeof vi.fn>;
  toJSON: () => { endpoint: string; keys: { p256dh: string; auth: string } };
}

interface FakePushManager {
  subscribe: ReturnType<typeof vi.fn>;
  getSubscription: ReturnType<typeof vi.fn>;
}

const SAMPLE_ENDPOINT = 'https://push.example.com/sub/abc123';

function makeFakeSubscription(): FakePushSubscription {
  return {
    endpoint: SAMPLE_ENDPOINT,
    unsubscribe: vi.fn().mockResolvedValue(true),
    toJSON: () => ({
      endpoint: SAMPLE_ENDPOINT,
      keys: { p256dh: 'p256dh-key', auth: 'auth-key' },
    }),
  };
}

interface InstallBrowserOptions {
  permission?: NotificationPermission;
  requestPermissionResult?: NotificationPermission;
  pushManager?: FakePushManager;
}

function installBrowser(options: InstallBrowserOptions): void {
  const pushManager =
    options.pushManager ??
    ({
      subscribe: vi.fn(),
      getSubscription: vi.fn().mockResolvedValue(null),
    } satisfies FakePushManager);

  Object.defineProperty(navigator, 'serviceWorker', {
    configurable: true,
    value: { ready: Promise.resolve({ pushManager }) },
  });
  (window as unknown as { PushManager: unknown }).PushManager = function PushManager() {
    /* boundary stub */
  };
  const NotificationStub = {
    permission: options.permission ?? 'default',
    requestPermission: vi
      .fn()
      .mockResolvedValue(options.requestPermissionResult ?? options.permission ?? 'granted'),
  };
  (window as unknown as { Notification: unknown }).Notification = NotificationStub;
  (globalThis as unknown as { Notification: unknown }).Notification = NotificationStub;
}

function uninstallBrowser(): void {
  Reflect.deleteProperty(navigator, 'serviceWorker');
  Reflect.deleteProperty(window as unknown as Record<string, unknown>, 'PushManager');
  Reflect.deleteProperty(window as unknown as Record<string, unknown>, 'Notification');
  Reflect.deleteProperty(globalThis as unknown as Record<string, unknown>, 'Notification');
}

afterEach(() => {
  uninstallBrowser();
  vi.clearAllMocks();
});

describe('PushToggle', () => {
  it('shows unsupported message with a disabled switch', async () => {
    uninstallBrowser();
    renderWithProviders(<PushToggle />);

    await waitFor(() => {
      expect(screen.getByText(/não são suportadas/i)).toBeInTheDocument();
    });
    expect(screen.getByRole('switch')).toBeDisabled();
  });

  it('shows blocked message when permission is denied', async () => {
    installBrowser({ permission: 'denied' });
    renderWithProviders(<PushToggle />);

    await waitFor(() => {
      expect(screen.getByText(/bloqueada/i)).toBeInTheDocument();
    });
    expect(screen.getByRole('switch')).toBeDisabled();
  });

  it('subscribes and toasts success when toggled on', async () => {
    const fakeSubscription = makeFakeSubscription();
    const pushManager: FakePushManager = {
      subscribe: vi.fn().mockResolvedValue(fakeSubscription),
      getSubscription: vi.fn().mockResolvedValue(null),
    };
    installBrowser({ requestPermissionResult: 'granted', pushManager });

    let subscribeCalls = 0;
    server.use(
      http.post('*/web-push/subscribe/', async ({ request }) => {
        const body = await request.json();
        subscribeCalls += 1;
        return HttpResponse.json(body, { status: 201 });
      }),
    );

    const user = userEvent.setup();
    renderWithProviders(<PushToggle />);

    const toggle = await screen.findByRole('switch');
    await waitFor(() => {
      expect(toggle).not.toBeDisabled();
    });

    await user.click(toggle);

    await waitFor(() => {
      expect(subscribeCalls).toBe(1);
    });
    expect(toast.success).toHaveBeenCalledWith('Notificações ativadas');
  });

  it('shows active state and unsubscribes with success toast when toggled off', async () => {
    const fakeSubscription = makeFakeSubscription();
    const pushManager: FakePushManager = {
      subscribe: vi.fn(),
      getSubscription: vi.fn().mockResolvedValue(fakeSubscription),
    };
    installBrowser({ permission: 'granted', pushManager });

    let unsubscribeCalls = 0;
    server.use(
      http.post('*/web-push/unsubscribe/', () => {
        unsubscribeCalls += 1;
        return new HttpResponse(null, { status: 204 });
      }),
    );

    const user = userEvent.setup();
    renderWithProviders(<PushToggle />);

    await waitFor(() => {
      expect(screen.getByText(/ativadas/i)).toBeInTheDocument();
    });
    const toggle = screen.getByRole('switch');
    expect(toggle).toBeChecked();

    await user.click(toggle);

    await waitFor(() => {
      expect(unsubscribeCalls).toBe(1);
    });
    expect(toast.success).toHaveBeenCalledWith('Notificações desativadas');
  });

  it('toasts an error in Portuguese when subscribe fails', async () => {
    const fakeSubscription = makeFakeSubscription();
    const pushManager: FakePushManager = {
      subscribe: vi.fn().mockResolvedValue(fakeSubscription),
      getSubscription: vi.fn().mockResolvedValue(null),
    };
    installBrowser({ requestPermissionResult: 'granted', pushManager });

    server.use(
      http.post('*/web-push/subscribe/', () => HttpResponse.json({ detail: 'falha' }, { status: 500 })),
    );

    const user = userEvent.setup();
    renderWithProviders(<PushToggle />);

    const toggle = await screen.findByRole('switch');
    await waitFor(() => {
      expect(toggle).not.toBeDisabled();
    });

    await user.click(toggle);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled();
    });
  });
});
