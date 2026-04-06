'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Loader2, Save, User, MapPin, Phone, TrendingUp, KeyRound } from 'lucide-react';
import { toast } from 'sonner';
import { useLandlord, useUpdateLandlord } from '@/lib/api/hooks/use-landlord';
import { useUpdateProfile, useChangePassword } from '@/lib/api/hooks/use-settings';
import {
  landlordFormSchema,
  type LandlordFormData,
} from '@/lib/schemas/landlord.schema';
import {
  profileFormSchema,
  changePasswordFormSchema,
  type ProfileFormValues,
  type ChangePasswordFormValues,
} from '@/lib/schemas/settings';
import { useAuthStore } from '@/store/auth-store';
import { MARITAL_STATUS_OPTIONS } from '@/lib/utils/constants';

export default function SettingsPage() {
  const { user, setUser } = useAuthStore();
  const { data: landlord, isLoading, error } = useLandlord();
  const updateMutation = useUpdateLandlord();
  const updateProfileMutation = useUpdateProfile();
  const changePasswordMutation = useChangePassword();

  const profileForm = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: {
      first_name: '',
      last_name: '',
    },
  });

  const passwordForm = useForm<ChangePasswordFormValues>({
    resolver: zodResolver(changePasswordFormSchema),
    defaultValues: {
      old_password: '',
      new_password: '',
      confirm_password: '',
    },
  });

  const form = useForm<LandlordFormData>({
    resolver: zodResolver(landlordFormSchema),
    defaultValues: {
      name: '',
      nationality: 'Brasileira',
      marital_status: '',
      cpf_cnpj: '',
      rg: '',
      phone: '',
      email: '',
      street: '',
      street_number: '',
      complement: '',
      neighborhood: '',
      city: '',
      state: '',
      zip_code: '',
      country: 'Brasil',
      rent_adjustment_percentage: 0,
      is_active: true,
    },
  });

  useEffect(() => {
    if (user) {
      profileForm.reset({
        first_name: user.first_name,
        last_name: user.last_name,
      });
    }
  }, [user, profileForm]);

  useEffect(() => {
    if (landlord) {
      form.reset({
        name: landlord.name ?? '',
        nationality: landlord.nationality ?? 'Brasileira',
        marital_status: landlord.marital_status ?? '',
        cpf_cnpj: landlord.cpf_cnpj ?? '',
        rg: landlord.rg ?? '',
        phone: landlord.phone ?? '',
        email: landlord.email ?? '',
        street: landlord.street ?? '',
        street_number: landlord.street_number ?? '',
        complement: landlord.complement ?? '',
        neighborhood: landlord.neighborhood ?? '',
        city: landlord.city ?? '',
        state: landlord.state ?? '',
        zip_code: landlord.zip_code ?? '',
        country: landlord.country ?? 'Brasil',
        rent_adjustment_percentage: landlord.rent_adjustment_percentage ?? 0,
        is_active: landlord.is_active ?? true,
      });
    }
  }, [landlord, form]);

  const onProfileSubmit = async (values: ProfileFormValues) => {
    try {
      const updated = await updateProfileMutation.mutateAsync(values);
      setUser(updated);
      toast.success('Perfil atualizado com sucesso');
    } catch {
      toast.error('Erro ao atualizar perfil');
    }
  };

  const onPasswordSubmit = async (values: ChangePasswordFormValues) => {
    try {
      await changePasswordMutation.mutateAsync({
        old_password: values.old_password,
        new_password: values.new_password,
      });
      toast.success('Senha alterada com sucesso');
      passwordForm.reset();
    } catch {
      toast.error('Erro ao alterar senha. Verifique sua senha atual.');
    }
  };

  const onSubmit = async (data: LandlordFormData) => {
    try {
      await updateMutation.mutateAsync(data);
      toast.success('Configurações salvas com sucesso!');
    } catch {
      toast.error('Erro ao salvar configurações');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const isNewLandlord = error?.response?.status === 404;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Configurações</h1>
        <p className="text-muted-foreground mt-1">
          Gerencie seu perfil e as informações do locador
        </p>
      </div>

      {/* Account section */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Minha Conta
          </CardTitle>
          <CardDescription>Atualize seu nome de exibição</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...profileForm}>
            <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-4">
              <div>
                <Label>Email</Label>
                <Input value={user?.email ?? ''} disabled className="mt-1" />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={profileForm.control}
                  name="first_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Nome *</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Seu nome"
                          {...field}
                          disabled={updateProfileMutation.isPending}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={profileForm.control}
                  name="last_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Sobrenome *</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Seu sobrenome"
                          {...field}
                          disabled={updateProfileMutation.isPending}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <Button type="submit" disabled={updateProfileMutation.isPending}>
                {updateProfileMutation.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-2" />
                )}
                Salvar Perfil
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5" />
            Alterar Senha
          </CardTitle>
          <CardDescription>Defina uma nova senha de acesso</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...passwordForm}>
            <form
              onSubmit={passwordForm.handleSubmit(onPasswordSubmit)}
              className="space-y-4 max-w-sm"
            >
              <FormField
                control={passwordForm.control}
                name="old_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Senha Atual *</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="••••••••"
                        {...field}
                        disabled={changePasswordMutation.isPending}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={passwordForm.control}
                name="new_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nova Senha *</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="••••••••"
                        {...field}
                        disabled={changePasswordMutation.isPending}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={passwordForm.control}
                name="confirm_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirmar Nova Senha *</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="••••••••"
                        {...field}
                        disabled={changePasswordMutation.isPending}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" disabled={changePasswordMutation.isPending}>
                {changePasswordMutation.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <KeyRound className="h-4 w-4 mr-2" />
                )}
                Alterar Senha
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Separator className="my-8" />

      {isNewLandlord && (
        <div className="mb-6 p-4 bg-primary/5 border border-primary/20 rounded-md">
          <p className="text-primary">
            Nenhum locador configurado. Preencha os dados abaixo para criar o primeiro registro.
          </p>
        </div>
      )}

      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Dados Pessoais
            </CardTitle>
            <CardDescription>
              Informações do locador que aparecerão nos contratos
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <Label htmlFor="name">Nome Completo *</Label>
              <Input
                id="name"
                {...form.register('name')}
                placeholder="Nome completo ou razão social"
              />
              {form.formState.errors.name && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.name.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="cpf_cnpj">CPF/CNPJ *</Label>
              <Input
                id="cpf_cnpj"
                {...form.register('cpf_cnpj')}
                placeholder="000.000.000-00"
              />
              {form.formState.errors.cpf_cnpj && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.cpf_cnpj.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="rg">RG</Label>
              <Input id="rg" {...form.register('rg')} placeholder="Opcional" />
            </div>

            <div>
              <Label htmlFor="nationality">Nacionalidade</Label>
              <Input id="nationality" {...form.register('nationality')} />
            </div>

            <div>
              <Label htmlFor="marital_status">Estado Civil *</Label>
              <Select
                value={form.watch('marital_status')}
                onValueChange={(value) => form.setValue('marital_status', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecione" />
                </SelectTrigger>
                <SelectContent>
                  {MARITAL_STATUS_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {form.formState.errors.marital_status && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.marital_status.message}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5" />
              Contato
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="phone">Telefone *</Label>
              <Input id="phone" {...form.register('phone')} placeholder="(00) 00000-0000" />
              {form.formState.errors.phone && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.phone.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                {...form.register('email')}
                placeholder="email@exemplo.com"
              />
              {form.formState.errors.email && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.email.message}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" />
              Endereço
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <Label htmlFor="street">Rua/Avenida *</Label>
              <Input id="street" {...form.register('street')} placeholder="Av. Circular" />
              {form.formState.errors.street && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.street.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="street_number">Número *</Label>
              <Input id="street_number" {...form.register('street_number')} placeholder="850" />
              {form.formState.errors.street_number && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.street_number.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="complement">Complemento</Label>
              <Input
                id="complement"
                {...form.register('complement')}
                placeholder="Apto, Sala, etc."
              />
            </div>

            <div>
              <Label htmlFor="neighborhood">Bairro *</Label>
              <Input
                id="neighborhood"
                {...form.register('neighborhood')}
                placeholder="Vila Jardim"
              />
              {form.formState.errors.neighborhood && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.neighborhood.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="zip_code">CEP *</Label>
              <Input id="zip_code" {...form.register('zip_code')} placeholder="00000-000" />
              {form.formState.errors.zip_code && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.zip_code.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="city">Cidade *</Label>
              <Input id="city" {...form.register('city')} placeholder="Porto Alegre" />
              {form.formState.errors.city && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.city.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="state">Estado *</Label>
              <Input id="state" {...form.register('state')} placeholder="Rio Grande do Sul" />
              {form.formState.errors.state && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.state.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="country">País</Label>
              <Input id="country" {...form.register('country')} />
            </div>
          </CardContent>
        </Card>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Reajuste de Aluguel
            </CardTitle>
            <CardDescription>
              Percentual padrão aplicado nos reajustes anuais de aluguel
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="max-w-xs">
              <Label htmlFor="rent_adjustment_percentage">Taxa de Reajuste Anual (%)</Label>
              <Input
                id="rent_adjustment_percentage"
                type="number"
                step="0.01"
                min="0"
                placeholder="Ex: 5.23"
                {...form.register('rent_adjustment_percentage', { valueAsNumber: true })}
              />
              {form.formState.errors.rent_adjustment_percentage && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.rent_adjustment_percentage.message}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" disabled={updateMutation.isPending}>
            {updateMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Salvar Configurações
          </Button>
        </div>
      </form>
    </div>
  );
}
