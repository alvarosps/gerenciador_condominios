import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useWebPush, urlBase64ToUint8Array } from '../use-web-push';
import { createWrapper } from '@/tests/test-utils';
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

interface SubscribePayload {
  endpoint: string;
  keys: { p256dh: string; auth: string };
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

function installBrowser(options: InstallBrowserOptions): { pushManager: FakePushManager } {
  const pushManager =
    options.pushManager ??
    ({
      subscribe: vi.fn(),
      getSubscription: vi.fn().mockResolvedValue(null),
    } satisfies FakePushManager);

  const serviceWorker = {
    ready: Promise.resolve({ pushManager }),
  };
  Object.defineProperty(navigator, 'serviceWorker', {
    configurable: true,
    value: serviceWorker,
  });

  // PushManager presence is detected via `'PushManager' in window`
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

  return { pushManager };
}

function uninstallBrowser(): void {
  Reflect.deleteProperty(navigator, 'serviceWorker');
  Reflect.deleteProperty(window as unknown as Record<string, unknown>, 'PushManager');
  Reflect.deleteProperty(window as unknown as Record<string, unknown>, 'Notification');
  Reflect.deleteProperty(globalThis as unknown as Record<string, unknown>, 'Notification');
}

afterEach(() => {
  uninstallBrowser();
});

describe('urlBase64ToUint8Array', () => {
  it('decodes a base64url VAPID key into a Uint8Array of the expected length', () => {
    // 65-byte uncompressed P-256 public key, base64url-encoded (no padding).
    const base64 =
      'BFqHj7yZ8nKQ0vEXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXAM';
    const result = urlBase64ToUint8Array(base64);
    expect(result).toBeInstanceOf(Uint8Array);
    expect(result.length).toBe(Math.floor((base64.length * 3) / 4));
  });

  it('produces deterministic bytes for a known key', () => {
    const result = urlBase64ToUint8Array('AAAA');
    expect(Array.from(result)).toEqual([0, 0, 0]);
  });
});

describe('useWebPush', () => {
  describe('when push is unsupported', () => {
    beforeEach(() => {
      uninstallBrowser();
    });

    it('reports unsupported and performs no HTTP on subscribe', async () => {
      let subscribeCalls = 0;
      server.use(
        http.post('*/web-push/subscribe/', () => {
          subscribeCalls += 1;
          return HttpResponse.json({}, { status: 201 });
        }),
      );

      const { result } = renderHook(() => useWebPush(), { wrapper: createWrapper() });

      await waitFor(() => {
        expect(result.current.permission).toBe('unsupported');
      });
      expect(result.current.isSupported).toBe(false);

      await act(async () => {
        await result.current.subscribe();
      });

      expect(subscribeCalls).toBe(0);
      expect(result.current.isSubscribed).toBe(false);
    });
  });

  describe('subscribe flow', () => {
    it('posts exactly { endpoint, keys: { p256dh, auth } } and marks subscribed', async () => {
      const fakeSubscription = makeFakeSubscription();
      const pushManager: FakePushManager = {
        subscribe: vi.fn().mockResolvedValue(fakeSubscription),
        getSubscription: vi.fn().mockResolvedValue(null),
      };
      installBrowser({ requestPermissionResult: 'granted', pushManager });

      let capturedBody: SubscribePayload | null = null;
      server.use(
        http.post('*/web-push/subscribe/', async ({ request }) => {
          // Test fixture boundary: MSW types the parsed body as DefaultBodyType (carve-out).
          const body = (await request.json()) as SubscribePayload;
          capturedBody = body;
          return HttpResponse.json(body, { status: 201 });
        }),
      );

      const { result } = renderHook(() => useWebPush(), { wrapper: createWrapper() });

      await waitFor(() => {
        expect(result.current.isSupported).toBe(true);
      });

      await act(async () => {
        await result.current.subscribe();
      });

      const subscribeArg = pushManager.subscribe.mock.calls[0]?.[0] as
        | { userVisibleOnly: boolean; applicationServerKey: Uint8Array }
        | undefined;
      expect(subscribeArg?.userVisibleOnly).toBe(true);
      expect(subscribeArg?.applicationServerKey).toBeInstanceOf(Uint8Array);

      expect(capturedBody).toEqual({
        endpoint: SAMPLE_ENDPOINT,
        keys: { p256dh: 'p256dh-key', auth: 'auth-key' },
      });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(true);
      });
      expect(result.current.permission).toBe('granted');
    });

    it('stops at denied permission without posting subscribe', async () => {
      const pushManager: FakePushManager = {
        subscribe: vi.fn(),
        getSubscription: vi.fn().mockResolvedValue(null),
      };
      installBrowser({ requestPermissionResult: 'denied', pushManager });

      let subscribeCalls = 0;
      server.use(
        http.post('*/web-push/subscribe/', () => {
          subscribeCalls += 1;
          return HttpResponse.json({}, { status: 201 });
        }),
      );

      const { result } = renderHook(() => useWebPush(), { wrapper: createWrapper() });

      await waitFor(() => {
        expect(result.current.isSupported).toBe(true);
      });

      await act(async () => {
        await result.current.subscribe();
      });

      expect(pushManager.subscribe).not.toHaveBeenCalled();
      expect(subscribeCalls).toBe(0);
      expect(result.current.permission).toBe('denied');
      expect(result.current.isSubscribed).toBe(false);
    });
  });

  describe('unsubscribe flow', () => {
    it('calls subscription.unsubscribe and posts { endpoint }', async () => {
      const fakeSubscription = makeFakeSubscription();
      const pushManager: FakePushManager = {
        subscribe: vi.fn(),
        getSubscription: vi.fn().mockResolvedValue(fakeSubscription),
      };
      installBrowser({ permission: 'granted', pushManager });

      let capturedBody: unknown = null;
      server.use(
        http.post('*/web-push/unsubscribe/', async ({ request }) => {
          capturedBody = await request.json();
          return new HttpResponse(null, { status: 204 });
        }),
      );

      const { result } = renderHook(() => useWebPush(), { wrapper: createWrapper() });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(true);
      });

      await act(async () => {
        await result.current.unsubscribe();
      });

      expect(fakeSubscription.unsubscribe).toHaveBeenCalled();
      expect(capturedBody).toEqual({ endpoint: SAMPLE_ENDPOINT });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(false);
      });
    });
  });

  describe('initial state', () => {
    it('reports subscribed when an existing subscription is present', async () => {
      const fakeSubscription = makeFakeSubscription();
      const pushManager: FakePushManager = {
        subscribe: vi.fn(),
        getSubscription: vi.fn().mockResolvedValue(fakeSubscription),
      };
      installBrowser({ permission: 'granted', pushManager });

      const { result } = renderHook(() => useWebPush(), { wrapper: createWrapper() });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(true);
      });
      expect(result.current.permission).toBe('granted');
    });
  });
});
