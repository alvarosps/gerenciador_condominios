'use client';

import { useEffect, useState } from 'react';
import { Menu } from 'lucide-react';
import { Sidebar } from './sidebar';
import { Header } from './header';
import { type ReactNode } from 'react';
import { useAuthStore } from '@/store/auth-store';
import { apiClient } from '@/lib/api/client';
import type { User } from '@/store/auth-store';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { ErrorBoundary } from '@/components/shared/error-boundary';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const { user, token, setUser } = useAuthStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Fetch user profile if we have a token but no user data (e.g., old session)
  useEffect(() => {
    if (token && !user) {
      void apiClient.get<User>('/auth/me/').then(({ data }) => {
        setUser(data);
      });
    }
  }, [token, user, setUser]);

  return (
    <div className="min-h-screen">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-background focus:text-foreground"
      >
        Pular para o conteúdo principal
      </a>
      {/* Mobile header - only visible on small screens */}
      <div className="fixed top-0 left-0 right-0 z-50 flex h-14 items-center border-b bg-background px-4 md:hidden">
        <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" onClick={() => setMobileMenuOpen(true)}>
              <Menu className="h-5 w-5" />
              <span className="sr-only">Menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0">
            <Sidebar onNavigate={() => setMobileMenuOpen(false)} />
          </SheetContent>
        </Sheet>
        <span className="ml-2 font-semibold">Condomínios Manager</span>
      </div>

      {/* Fixed Sidebar - Hidden on mobile, visible on md+ */}
      <aside className="hidden md:block fixed left-0 top-0 bottom-0 w-64 h-screen overflow-auto bg-card border-r">
        <Sidebar />
      </aside>

      {/* Main Content Area - Full width on mobile, margin on md+ */}
      <div className="pt-14 md:pt-0 md:ml-64">
        <Header />
        <ErrorBoundary>
          <main id="main-content" className="p-4 md:p-6 bg-muted/30 min-h-[calc(100vh-73px)]">
            {children}
          </main>
        </ErrorBoundary>
      </div>
    </div>
  );
}
