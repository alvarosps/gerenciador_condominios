'use client';

import { User, Home, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useTenantProfile } from '@/lib/api/hooks/use-tenant-portal';

function ProfileSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-7 w-32" />
      <Skeleton className="h-40 w-full rounded-lg" />
      <Skeleton className="h-32 w-full rounded-lg" />
      <Skeleton className="h-24 w-full rounded-lg" />
    </div>
  );
}

interface LabelValueProps {
  label: string;
  value: string | number | null | undefined;
}

function LabelValue({ label, value }: LabelValueProps) {
  return (
    <div className="py-2 border-b last:border-b-0">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value ?? '—'}</p>
    </div>
  );
}

export default function TenantProfilePage() {
  const { data: profile, isLoading, isError } = useTenantProfile();

  if (isLoading) {
    return <ProfileSkeleton />;
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Erro ao carregar seu perfil. Por favor, tente novamente.
        </AlertDescription>
      </Alert>
    );
  }

  if (!profile) {
    return null;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Meu Perfil</h2>

      {/* Personal data */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <User className="h-4 w-4" />
            Dados Pessoais
          </CardTitle>
        </CardHeader>
        <CardContent>
          <LabelValue label="Nome" value={profile.name} />
          <LabelValue label="CPF / CNPJ" value={profile.cpf_cnpj} />
          <LabelValue label="Telefone" value={profile.phone} />
          <LabelValue label="Estado Civil" value={profile.marital_status} />
          <LabelValue label="Profissão" value={profile.profession} />
        </CardContent>
      </Card>

      {/* Apartment info */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Home className="h-4 w-4" />
            Imóvel
          </CardTitle>
        </CardHeader>
        <CardContent>
          <LabelValue label="Apartamento" value={profile.apartment.number} />
          <LabelValue label="Prédio" value={profile.apartment.building_name} />
          <LabelValue label="Endereço" value={profile.apartment.building_address} />
          <LabelValue label="Vencimento" value={`Todo dia ${profile.due_day}`} />
        </CardContent>
      </Card>

      {/* Dependents */}
      {profile.dependents.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Users className="h-4 w-4" />
              Dependentes
            </CardTitle>
          </CardHeader>
          <CardContent>
            {profile.dependents.map((dep) => (
              <div key={dep.id} className="py-2 border-b last:border-b-0">
                <p className="text-sm font-medium">{dep.name}</p>
                {dep.phone && (
                  <p className="text-xs text-muted-foreground">{dep.phone}</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
