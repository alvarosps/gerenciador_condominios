'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, CreditCard, FileText, Bell, User, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/auth-store';
import { useLogout } from '@/lib/api/hooks/use-auth';

interface TenantPortalLayoutProps {
  children: ReactNode;
}

const NAV_ITEMS = [
  { href: '/tenant', label: 'Início', icon: Home },
  { href: '/tenant/payments', label: 'Pagamentos', icon: CreditCard },
  { href: '/tenant/contract', label: 'Contrato', icon: FileText },
  { href: '/tenant/notifications', label: 'Avisos', icon: Bell },
  { href: '/tenant/profile', label: 'Perfil', icon: User },
];

export function TenantPortalLayout({ children }: TenantPortalLayoutProps) {
  const user = useAuthStore((state) => state.user);
  const logoutMutation = useLogout();
  const pathname = usePathname();

  const handleLogout = (): void => {
    logoutMutation.mutate();
  };

  return (
    <div className="min-h-screen flex flex-col bg-muted/30">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-card border-b px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="font-semibold text-base">Portal do Inquilino</h1>
          {user && (
            <p className="text-xs text-muted-foreground">
              {user.first_name} {user.last_name}
            </p>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleLogout}
          disabled={logoutMutation.isPending}
          aria-label="Sair"
        >
          <LogOut className="h-4 w-4 mr-1" />
          <span className="text-sm">Sair</span>
        </Button>
      </header>

      {/* Main content */}
      <main className="flex-1 p-4 pb-20">{children}</main>

      {/* Bottom navigation */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 bg-card border-t">
        <ul className="flex items-stretch">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href;
            return (
              <li key={href} className="flex-1">
                <Link
                  href={href}
                  className={`flex flex-col items-center justify-center py-2 px-1 text-xs gap-1 transition-colors ${
                    isActive
                      ? 'text-primary font-medium'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span>{label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
