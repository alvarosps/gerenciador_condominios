'use client';

import Link from 'next/link';
import { CreditCard, FileText, Bell, Home } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuthStore } from '@/store/auth-store';
import { useTenantProfile } from '@/lib/api/hooks/use-tenant-portal';
import { formatCurrency } from '@/lib/utils/formatters';

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-6 w-64" />
      <Skeleton className="h-28 w-full rounded-lg" />
      <div className="grid grid-cols-2 gap-3">
        <Skeleton className="h-24 rounded-lg" />
        <Skeleton className="h-24 rounded-lg" />
        <Skeleton className="h-24 rounded-lg" />
        <Skeleton className="h-24 rounded-lg" />
      </div>
    </div>
  );
}

const QUICK_ACTIONS = [
  {
    href: '/tenant/payments',
    label: 'Pagamentos',
    description: 'Histórico e comprovantes',
    icon: CreditCard,
  },
  {
    href: '/tenant/contract',
    label: 'Contrato',
    description: 'Visualizar contrato',
    icon: FileText,
  },
  {
    href: '/tenant/notifications',
    label: 'Avisos',
    description: 'Comunicados do condomínio',
    icon: Bell,
  },
  {
    href: '/tenant/profile',
    label: 'Meu Perfil',
    description: 'Dados pessoais',
    icon: Home,
  },
];

export default function TenantDashboardPage() {
  const user = useAuthStore((state) => state.user);
  const { data: profile, isLoading, isError } = useTenantProfile();

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Erro ao carregar seus dados. Por favor, tente novamente.
        </AlertDescription>
      </Alert>
    );
  }

  const rentalValue = profile ? parseFloat(profile.lease.rental_value) : 0;

  return (
    <div className="space-y-4">
      {/* Greeting */}
      <div>
        <h2 className="text-xl font-bold">
          Olá, {user?.first_name ?? profile?.name.split(' ')[0]}!
        </h2>
        {profile && (
          <p className="text-sm text-muted-foreground">
            Apartamento {profile.apartment.number} — {profile.apartment.building_name}
          </p>
        )}
      </div>

      {/* Rent card */}
      {profile && (
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-muted-foreground">Aluguel mensal</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{formatCurrency(rentalValue)}</p>
            <p className="text-sm text-muted-foreground mt-1">
              Vencimento todo dia {profile.due_day}
            </p>
            {profile.lease.pending_rental_value && (
              <p className="text-xs text-amber-600 mt-1">
                Novo valor: {formatCurrency(parseFloat(profile.lease.pending_rental_value))} a
                partir de{' '}
                {profile.lease.pending_rental_value_date
                  ? new Date(profile.lease.pending_rental_value_date).toLocaleDateString('pt-BR')
                  : ''}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-3">
        {QUICK_ACTIONS.map(({ href, label, description, icon: Icon }) => (
          <Link key={href} href={href}>
            <Card className="h-full hover:bg-accent/50 transition-colors cursor-pointer">
              <CardContent className="pt-4 pb-3 flex flex-col items-center text-center gap-2">
                <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary/10">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="font-medium text-sm">{label}</p>
                  <p className="text-xs text-muted-foreground">{description}</p>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
