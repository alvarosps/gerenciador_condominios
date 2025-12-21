'use client';

import { Sidebar } from './sidebar';
import { Header } from './header';
import { ReactNode } from 'react';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-screen">
      {/* Fixed Sidebar */}
      <aside className="fixed left-0 top-0 bottom-0 w-64 h-screen overflow-auto bg-white border-r">
        <Sidebar />
      </aside>

      {/* Main Content Area with margin for fixed sidebar */}
      <div className="ml-64">
        <Header />
        <main className="p-6 bg-muted/30">
          {children}
        </main>
      </div>
    </div>
  );
}
