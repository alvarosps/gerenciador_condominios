'use client';

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { User, Home, Users, Bell, Pencil, Loader2, Save, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { useTenantProfile, useUpdateTenantPhone } from '@/lib/api/hooks/use-tenant-portal';
import { PushToggle } from '@/components/notifications/push-toggle';
import { getErrorMessage } from '@/lib/utils/error-handler';

const phoneFormSchema = z.object({
  phone: z.string().min(1, 'Telefone é obrigatório'),
});

type PhoneFormValues = z.infer<typeof phoneFormSchema>;

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

function PhoneField({ phone }: { phone: string }) {
  const [isEditing, setIsEditing] = useState(false);
  const updatePhone = useUpdateTenantPhone();

  const form = useForm<PhoneFormValues>({
    resolver: zodResolver(phoneFormSchema),
    defaultValues: { phone },
  });

  useEffect(() => {
    form.reset({ phone });
  }, [phone, form]);

  const handleSubmit = async (values: PhoneFormValues) => {
    try {
      await updatePhone.mutateAsync(values.phone);
      toast.success('Telefone atualizado com sucesso!');
      setIsEditing(false);
    } catch (error) {
      toast.error(getErrorMessage(error, 'Erro ao atualizar telefone'));
    }
  };

  if (!isEditing) {
    return (
      <div className="py-2 border-b last:border-b-0 flex items-center justify-between">
        <div>
          <p className="text-xs text-muted-foreground">Telefone</p>
          <p className="text-sm font-medium">{phone || '—'}</p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsEditing(true)}
          aria-label="Editar telefone"
        >
          <Pencil className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <Form {...form}>
      <form
        onSubmit={(e) => void form.handleSubmit(handleSubmit)(e)}
        className="py-2 border-b last:border-b-0 space-y-2"
      >
        <FormField
          control={form.control}
          name="phone"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-xs text-muted-foreground">Telefone</FormLabel>
              <FormControl>
                <Input {...field} placeholder="(00) 00000-0000" disabled={updatePhone.isPending} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex gap-2">
          <Button type="submit" size="sm" disabled={updatePhone.isPending}>
            {updatePhone.isPending ? (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-1" />
            )}
            Salvar
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              form.reset({ phone });
              setIsEditing(false);
            }}
            disabled={updatePhone.isPending}
          >
            <X className="h-4 w-4 mr-1" />
            Cancelar
          </Button>
        </div>
      </form>
    </Form>
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

      {/* Notifications */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Notificações
          </CardTitle>
        </CardHeader>
        <CardContent>
          <PushToggle />
        </CardContent>
      </Card>

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
          <PhoneField phone={profile.phone} />
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
          {profile.apartment ? (
            <>
              <LabelValue label="Apartamento" value={profile.apartment.number} />
              <LabelValue label="Prédio" value={profile.apartment.building_name} />
              <LabelValue label="Endereço" value={profile.apartment.building_address} />
              <LabelValue label="Vencimento" value={`Todo dia ${profile.due_day}`} />
            </>
          ) : (
            <p className="text-sm text-muted-foreground py-2">Nenhuma locação ativa</p>
          )}
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
                {dep.phone && <p className="text-xs text-muted-foreground">{dep.phone}</p>}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
