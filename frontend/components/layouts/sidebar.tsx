'use client';

import { useState } from 'react';
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
  DollarSign,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';
import { ROUTES } from '@/lib/utils/constants';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

interface MenuItem {
  key: string;
  icon: React.ReactNode;
  label: string;
  children?: SubMenuItem[];
}

interface SubMenuItem {
  key: string;
  label: string;
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [expandedMenus, setExpandedMenus] = useState<Record<string, boolean>>({});

  const financialChildren: SubMenuItem[] = [
    { key: ROUTES.FINANCIAL, label: 'Dashboard' },
    { key: ROUTES.FINANCIAL_DAILY, label: 'Controle Diário' },
    { key: ROUTES.FINANCIAL_EXPENSES, label: 'Despesas' },
    { key: ROUTES.FINANCIAL_INCOMES, label: 'Receitas' },
    { key: ROUTES.FINANCIAL_RENT_PAYMENTS, label: 'Pgto. Aluguel' },
    { key: ROUTES.FINANCIAL_PERSONS, label: 'Pessoas' },
    { key: ROUTES.FINANCIAL_PERSON_PAYMENTS, label: 'Pgto. Pessoas' },
    { key: ROUTES.FINANCIAL_PERSON_INCOMES, label: 'Rendimentos' },
    { key: ROUTES.FINANCIAL_EMPLOYEES, label: 'Funcionários' },
    { key: ROUTES.FINANCIAL_CATEGORIES, label: 'Categorias' },
    { key: ROUTES.FINANCIAL_SIMULATOR, label: 'Simulador' },
    { key: ROUTES.FINANCIAL_SETTINGS, label: 'Configurações' },
  ];

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
      key: ROUTES.FINANCIAL,
      icon: <DollarSign className="h-5 w-5" />,
      label: 'Financeiro',
      children: financialChildren,
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

  const toggleExpanded = (key: string): void => {
    setExpandedMenus((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const isChildActive = (children: SubMenuItem[]): boolean => {
    return children.some((child) => pathname === child.key);
  };

  const handleApiDocsClick = (): void => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api';
    window.open(`${apiUrl}/schema/swagger-ui/`, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="h-full bg-card flex flex-col">
      <div className="p-4 border-b">
        <h1 className="text-xl font-bold text-primary">Condomínios Manager</h1>
      </div>

      <nav className="flex-1 py-2">
        {mainMenuItems.map((item) => {
          if (item.children) {
            const isExpanded = expandedMenus[item.key] ?? false;
            const hasActiveChild = isChildActive(item.children);

            return (
              <div key={item.key}>
                <button
                  onClick={() => toggleExpanded(item.key)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors',
                    hasActiveChild
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )}
                >
                  {item.icon}
                  <span className="flex-1 text-left">{item.label}</span>
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </button>
                {isExpanded && (
                  <div>
                    {item.children.map((child) => {
                      const isActive = pathname === child.key;
                      return (
                        <button
                          key={child.key}
                          onClick={() => handleMenuClick(child.key)}
                          className={cn(
                            'w-full flex items-center gap-3 pl-12 pr-4 py-2 text-sm transition-colors',
                            isActive
                              ? 'bg-primary/10 text-primary border-r-4 border-primary font-medium'
                              : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                          )}
                        >
                          <span>{child.label}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          }

          const isActive = pathname === item.key;
          return (
            <button
              key={item.key}
              onClick={() => handleMenuClick(item.key)}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary border-r-4 border-primary'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground',
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
