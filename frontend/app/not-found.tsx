'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';

export const dynamic = 'force-dynamic';

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="text-center space-y-4">
        <h1 className="text-6xl font-bold mb-4">404</h1>
        <p className="text-xl text-muted-foreground mb-8">
          Desculpe, a página que você visitou não existe.
        </p>
        <Button asChild size="lg">
          <Link href="/">Voltar para Home</Link>
        </Button>
      </div>
    </div>
  );
}
