import { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../client';

export type PushPermissionState = 'unsupported' | 'default' | 'denied' | 'granted';

export interface UseWebPushResult {
  isSupported: boolean;
  permission: PushPermissionState;
  isSubscribed: boolean;
  isPending: boolean;
  subscribe: () => Promise<void>;
  unsubscribe: () => Promise<void>;
}

/**
 * Convert a base64url-encoded VAPID public key into the Uint8Array required by
 * `PushManager.subscribe`'s `applicationServerKey`.
 */
export function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4);
  const normalized = (base64 + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(normalized);
  const output = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i += 1) {
    output[i] = raw.charCodeAt(i);
  }
  return output;
}

function detectSupport(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    'serviceWorker' in navigator &&
    typeof window !== 'undefined' &&
    'PushManager' in window
  );
}

export function useWebPush(): UseWebPushResult {
  const [isSupported] = useState(detectSupport);
  const [permission, setPermission] = useState<PushPermissionState>(
    isSupported ? 'default' : 'unsupported',
  );
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isPending, setIsPending] = useState(false);

  useEffect(() => {
    if (!isSupported) return;

    let cancelled = false;
    void (async () => {
      setPermission(Notification.permission);
      const registration = await navigator.serviceWorker.ready;
      const existing = await registration.pushManager.getSubscription();
      if (!cancelled) {
        setIsSubscribed(existing !== null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isSupported]);

  const subscribe = useCallback(async () => {
    if (!isSupported) return;

    setIsPending(true);
    try {
      const result = await Notification.requestPermission();
      if (result !== 'granted') {
        setPermission(result);
        return;
      }

      const { data } = await apiClient.get<{ publicKey: string }>('/web-push/vapid-public-key/');
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(data.publicKey),
      });

      await apiClient.post('/web-push/subscribe/', subscription.toJSON());
      setPermission('granted');
      setIsSubscribed(true);
    } finally {
      setIsPending(false);
    }
  }, [isSupported]);

  const unsubscribe = useCallback(async () => {
    if (!isSupported) return;

    setIsPending(true);
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription === null) {
        setIsSubscribed(false);
        return;
      }

      await subscription.unsubscribe();
      await apiClient.post('/web-push/unsubscribe/', { endpoint: subscription.endpoint });
      setIsSubscribed(false);
    } finally {
      setIsPending(false);
    }
  }, [isSupported]);

  return { isSupported, permission, isSubscribed, isPending, subscribe, unsubscribe };
}
