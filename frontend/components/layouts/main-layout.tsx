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
      {/* Fixed Sidebar - Hidden on mobile, visible on md+ */}
      <aside className="hidden md:block fixed left-0 top-0 bottom-0 w-64 h-screen overflow-auto bg-white border-r">
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
