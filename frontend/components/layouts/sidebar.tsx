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
  Wallet,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';
import { ROUTES } from '@/lib/utils/constants';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/auth-store';

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

interface SidebarProps {
  onNavigate?: () => void;
}

/**
 * A route key is a "candidate" for the current pathname when it is an exact match or a path
 * segment prefix of it (`/finances/accounts` matches `/finances/accounts/7`, never
 * `/finances/accountsX`).
 */
function isRouteCandidate(pathname: string, key: string): boolean {
  return pathname === key || pathname.startsWith(`${key}/`);
}

/**
 * Longest-match route resolution: among every key in `keys` that is a candidate for `pathname`
 * (see `isRouteCandidate`), only the longest one is the active route. Plain prefix matching is
 * not enough — sibling routes are themselves prefixes of one another (e.g. `/financial` is a
 * prefix of `/financial/expenses`), so without picking the longest candidate a parent route
 * would falsely light up alongside its more specific sibling/child.
 */
function resolveActiveKey(pathname: string, keys: string[]): string | null {
  let best: string | null = null;
  for (const key of keys) {
    if (!isRouteCandidate(pathname, key)) continue;
    if (best === null || key.length > best.length) best = key;
  }
  return best;
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuthStore();
  const isStaff = user?.is_staff ?? false;
  const [expandedMenus, setExpandedMenus] = useState<Record<string, boolean>>({});

  const financialChildren: SubMenuItem[] = [
    { key: ROUTES.FINANCIAL, label: 'Dashboard' },
    { key: ROUTES.FINANCIAL_DAILY, label: 'Controle Diário' },
    { key: ROUTES.FINANCIAL_EXPENSES, label: 'Despesas' },
    { key: ROUTES.FINANCIAL_MONTHLY_PURCHASES, label: 'Compras do Mês' },
    { key: ROUTES.FINANCIAL_INCOMES, label: 'Receitas' },
    { key: ROUTES.FINANCIAL_RENT_PAYMENTS, label: 'Pgto. Aluguel' },
    { key: ROUTES.FINANCIAL_PERSONS, label: 'Pessoas' },
    { key: ROUTES.FINANCIAL_PERSON_PAYMENTS, label: 'Pgto. Pessoas' },
    { key: ROUTES.FINANCIAL_PERSON_INCOMES, label: 'Rendimentos' },
    { key: ROUTES.FINANCIAL_EMPLOYEES, label: 'Funcionários' },
    { key: ROUTES.FINANCIAL_CATEGORIES, label: 'Categorias' },
    { key: ROUTES.FINANCIAL_SIMULATOR, label: 'Simulador' },
    { key: ROUTES.FINANCIAL_MONTH_ADVANCE, label: 'Virada de Mês' },
    { key: ROUTES.FINANCIAL_SETTINGS, label: 'Configurações' },
  ];

  // New "Condomínio" finances module — separate from the legacy "Financeiro" group.
  const condominioChildren: SubMenuItem[] = [
    { key: ROUTES.FINANCES_BILLS, label: 'Contas' },
    { key: ROUTES.FINANCES_ACCOUNTS, label: 'Contas cadastradas' },
    { key: ROUTES.FINANCES_INSTALLMENT_PLANS, label: 'Parcelas' },
    { key: ROUTES.FINANCES_EMPLOYEES, label: 'Folha' },
    { key: ROUTES.FINANCES_THIRD_PARTY, label: 'Terceiros' },
    { key: ROUTES.FINANCES_RESERVE, label: 'Reserva' },
    { key: ROUTES.FINANCES_INCOME, label: 'Receitas' },
    { key: ROUTES.FINANCES_MONTH_CLOSE, label: 'Fechamento' },
    { key: ROUTES.FINANCES_PROJECTION, label: 'Projeção' },
    { key: ROUTES.FINANCES_DISTRIBUTION, label: 'Distribuição' },
    { key: ROUTES.FINANCES_CATEGORIES, label: 'Categorias' },
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
      label: 'Financeiro (legado)',
      children: financialChildren,
    },
    {
      key: ROUTES.FINANCES_BILLS,
      icon: <Wallet className="h-5 w-5" />,
      label: 'Condomínio',
      children: condominioChildren,
    },
    {
      key: ROUTES.SETTINGS,
      icon: <Settings className="h-5 w-5" />,
      label: 'Configurações',
    },
    ...(isStaff
      ? [
          {
            key: ROUTES.ADMIN_USERS,
            icon: <ShieldCheck className="h-5 w-5" />,
            label: 'Usuários',
          },
        ]
      : []),
  ];

  // Single longest-match resolution across every route in the sidebar (root items + every
  // group's children) — a route is active only if its key is the longest candidate for the
  // current pathname among ALL of them, so a group's root key (e.g. FINANCES_BILLS, reused as
  // "Condomínio") never outranks a more specific child (e.g. FINANCES_ACCOUNTS) and vice versa.
  const allRouteKeys = mainMenuItems.flatMap((item) => [
    item.key,
    ...(item.children ?? []).map((child) => child.key),
  ]);
  const activeKey = resolveActiveKey(pathname, allRouteKeys);

  const isChildActive = (children: SubMenuItem[]): boolean => {
    return children.some((child) => child.key === activeKey);
  };

  const handleMenuClick = (key: string): void => {
    router.push(key);
    onNavigate?.();
  };

  const toggleExpanded = (key: string): void => {
    setExpandedMenus((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleApiDocsClick = (): void => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api';
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
            const hasActiveChild = isChildActive(item.children);
            // A group starts expanded when it owns the active route; once the user
            // explicitly toggles it, that choice (in expandedMenus) takes over.
            const isExpanded = expandedMenus[item.key] ?? hasActiveChild;

            return (
              <div key={item.key}>
                <button
                  onClick={() => toggleExpanded(item.key)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors',
                    hasActiveChild
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
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
                      const isActive = child.key === activeKey;
                      return (
                        <button
                          key={child.key}
                          onClick={() => handleMenuClick(child.key)}
                          className={cn(
                            'w-full flex items-center gap-3 pl-12 pr-4 py-2 text-sm transition-colors',
                            isActive
                              ? 'bg-primary/10 text-primary border-r-4 border-primary font-medium'
                              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
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

          const isActive = item.key === activeKey;
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
            <span>Documentação da API</span>
          </button>
        </div>
      </div>
    </div>
  );
}
