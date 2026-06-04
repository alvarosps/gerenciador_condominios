/// <reference lib="webworker" />
import { defaultCache } from '@serwist/next/worker';
import type { PrecacheEntry, SerwistGlobalConfig } from 'serwist';
import { Serwist } from 'serwist';

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    // Injetado pelo build do Serwist (precache do app shell — manifest da S28).
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope;

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: defaultCache,
  fallbacks: {
    entries: [
      {
        url: '/offline',
        matcher: ({ request }) => request.destination === 'document',
      },
    ],
  },
});

serwist.addEventListeners();

// =====================================================================
// === Web Push handlers (Sessão 33) ===
// Listeners 'push' (self.registration.showNotification) e 'notificationclick'
// (focar/abrir a aba na rota mapeada de event.notification.data.screen).
// =====================================================================

interface PushPayload {
  title: string;
  body: string;
  data?: { screen?: string };
}

// data.screen do backend (bare) → rota web real; fallback '/'
const SCREEN_TO_PATH: Record<string, string> = {
  proofs: '/',
  payments: '/tenant/payments',
};

function parsePushPayload(raw: unknown): PushPayload | undefined {
  if (typeof raw !== 'object' || raw === null) return undefined;
  if (!('title' in raw) || !('body' in raw)) return undefined;
  if (typeof raw.title !== 'string' || typeof raw.body !== 'string') return undefined;
  const screen =
    'data' in raw &&
    typeof raw.data === 'object' &&
    raw.data !== null &&
    'screen' in raw.data &&
    typeof raw.data.screen === 'string'
      ? raw.data.screen
      : undefined;
  return { title: raw.title, body: raw.body, data: screen !== undefined ? { screen } : {} };
}

function screenToPath(data: unknown): string {
  const screen =
    typeof data === 'object' && data !== null && 'screen' in data && typeof data.screen === 'string'
      ? data.screen
      : undefined;
  return screen ? (SCREEN_TO_PATH[screen] ?? '/') : '/';
}

async function focusOrOpen(path: string): Promise<void> {
  const windowClients = await self.clients.matchAll({
    type: 'window',
    includeUncontrolled: true,
  });
  const existing = windowClients.find((client) => new URL(client.url).pathname === path);
  if (existing) {
    await existing.focus();
    return;
  }
  await self.clients.openWindow(path);
}

self.addEventListener('push', (event) => {
  const payload = parsePushPayload(event.data?.json());
  if (!payload) return;
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-192.png',
      data: payload.data ?? {},
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const data: unknown = event.notification.data;
  event.waitUntil(focusOrOpen(screenToPath(data)));
});
