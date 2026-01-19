'use client';

import {
  Home,
  Building2,
  DoorOpen,
  Users,
  FileText,
  Package,
  FileEdit,
  BookOpen,
  Settings,
} from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';
import { ROUTES } from '@/lib/utils/constants';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

interface MenuItem {
  key: string;
  icon: React.ReactNode;
  label: string;
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const mainMenuItems: MenuItem[] = [
    {
      key: ROUTES.DASHBOARD,
      icon: <Home className="h-5 w-5" />,
      label: 'Dashboard',
    },
    {
      key: ROUTES.BUILDINGS,
      icon: <Building2 className="h-5 w-5" />,
      label: 'Prédios',
    },
    {
      key: ROUTES.APARTMENTS,
      icon: <DoorOpen className="h-5 w-5" />,
      label: 'Apartamentos',
    },
    {
      key: ROUTES.TENANTS,
      icon: <Users className="h-5 w-5" />,
      label: 'Inquilinos',
    },
    {
      key: ROUTES.LEASES,
      icon: <FileText className="h-5 w-5" />,
      label: 'Locações',
    },
    {
      key: ROUTES.FURNITURE,
      icon: <Package className="h-5 w-5" />,
      label: 'Móveis',
    },
    {
      key: ROUTES.CONTRACT_TEMPLATE,
      icon: <FileEdit className="h-5 w-5" />,
      label: 'Template de Contrato',
    },
    {
      key: ROUTES.SETTINGS,
      icon: <Settings className="h-5 w-5" />,
      label: 'Configurações',
    },
  ];

  const handleMenuClick = (key: string): void => {
    router.push(key);
  };

  const handleApiDocsClick = (): void => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
    window.open(`${apiUrl}/schema/swagger-ui/`, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="h-full bg-white flex flex-col">
      <div className="p-4 border-b">
        <h1 className="text-xl font-bold text-primary">Condomínios Manager</h1>
      </div>

      <nav className="flex-1 py-2">
        {mainMenuItems.map((item) => {
          const isActive = pathname === item.key;
          return (
            <button
              key={item.key}
              onClick={() => handleMenuClick(item.key)}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary border-r-4 border-primary'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="mt-auto">
        <Separator className="my-2" />
        <div className="px-4 pb-4">
          <button
            onClick={handleApiDocsClick}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
          >
            <BookOpen className="h-5 w-5" />
            <span>API Documentation</span>
          </button>
        </div>
      </div>
    </div>
  );
}
