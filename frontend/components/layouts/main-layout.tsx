'use client';

import { useEffect } from 'react';
import { Sidebar } from './sidebar';
import { Header } from './header';
import { type ReactNode } from 'react';
import { useAuthStore } from '@/store/auth-store';
import { apiClient } from '@/lib/api/client';
import type { User } from '@/store/auth-store';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const { user, token, setUser } = useAuthStore();

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
      {/* Fixed Sidebar - Hidden on mobile, visible on md+ */}
      <aside className="hidden md:block fixed left-0 top-0 bottom-0 w-64 h-screen overflow-auto bg-card border-r">
        <Sidebar />
      </aside>

      {/* Main Content Area - Full width on mobile, margin on md+ */}
      <div className="md:ml-64">
        <Header />
        <main className="p-4 md:p-6 bg-muted/30 min-h-[calc(100vh-73px)]">
          {children}
        </main>
      </div>
    </div>
  );
}
