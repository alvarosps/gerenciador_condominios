'use client';

import { Suspense, useEffect, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { toast } from 'sonner';
import { Loading } from '@/components/shared/loading';
import { useExchangeOAuthCode } from '@/lib/api/hooks/use-auth';

// Force dynamic rendering — the callback depends entirely on runtime query params
export const dynamic = 'force-dynamic';

/**
 * Inner component that reads the OAuth result from the URL.
 * Must live under a <Suspense> boundary because useSearchParams() suspends
 * during static rendering (Next.js 14 App Router requirement).
 */
function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const exchangeOAuthCode = useExchangeOAuthCode();
  const hasRun = useRef(false);

  useEffect(() => {
    // Guard against re-running on re-render — the exchange must happen exactly once
    if (hasRun.current) {
      return;
    }
    hasRun.current = true;

    const error = searchParams.get('error');
    const code = searchParams.get('code');

    if (error) {
      toast.error('Falha no login com Google.');
      router.replace('/login');
      return;
    }

    if (!code) {
      // No code and no error: a direct hit or a misconfigured backend redirect.
      // Surface it instead of bouncing silently, so setup issues are observable.
      toast.error('Sessão de login inválida.');
      router.replace('/login');
      return;
    }

    exchangeOAuthCode.mutate(
      { code },
      {
        onSuccess: () => {
          router.replace('/');
        },
        onError: () => {
          toast.error('Não foi possível concluir o login com Google.');
          router.replace('/login');
        },
      }
    );
  }, [exchangeOAuthCode, router, searchParams]);

  return <Loading tip="Concluindo login com Google..." fullScreen />;
}

/**
 * Google OAuth callback page — receives the allauth redirect with a short-lived
 * code, exchanges it for an authenticated session, then routes the user onward.
 */
export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<Loading fullScreen />}>
      <OAuthCallbackContent />
    </Suspense>
  );
}
