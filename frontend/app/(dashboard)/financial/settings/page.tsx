'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import {
  useFinancialSettings,
  useUpdateFinancialSettings,
} from '@/lib/api/hooks/use-financial-settings';
import { useAuthStore } from '@/store/auth-store';

const settingsFormSchema = z.object({
  initial_balance: z.string().min(1, 'Saldo inicial é obrigatório'),
  initial_balance_date: z.string().min(1, 'Data do saldo inicial é obrigatória'),
  notes: z.string(),
});

type SettingsFormValues = z.infer<typeof settingsFormSchema>;

export default function FinancialSettingsPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;
  const { data: settings, isLoading } = useFinancialSettings();
  const updateMutation = useUpdateFinancialSettings();

  const formMethods = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsFormSchema),
    defaultValues: {
      initial_balance: '0',
      initial_balance_date: '',
      notes: '',
    },
  });

  useEffect(() => {
    if (settings) {
      formMethods.reset({
        initial_balance: String(settings.initial_balance),
        initial_balance_date: settings.initial_balance_date,
        notes: settings.notes ?? '',
      });
    }
  }, [settings, formMethods]);

  const onSubmit = async (values: SettingsFormValues) => {
    try {
      await updateMutation.mutateAsync({
        initial_balance: Number(values.initial_balance),
        initial_balance_date: values.initial_balance_date,
        notes: values.notes ?? '',
      });
      toast.success('Configurações salvas com sucesso');
    } catch (error) {
      toast.error('Erro ao salvar configurações');
      console.error('Save error:', error);
    }
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="text-2xl font-bold">Configurações Financeiras</h1>
        <p className="text-muted-foreground mt-1">Carregando...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Configurações Financeiras</h1>
        <p className="text-muted-foreground mt-1">Configure o saldo inicial e parâmetros do módulo financeiro</p>
      </div>

      <div className="max-w-lg">
        <Form {...formMethods}>
          <form onSubmit={formMethods.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={formMethods.control}
              name="initial_balance"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Saldo Inicial (R$) *</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="Ex: 10000.00"
                      {...field}
                      disabled={updateMutation.isPending || !isAdmin}
                    />
                  </FormControl>
                  <FormDescription>Valor do saldo inicial em reais</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={formMethods.control}
              name="initial_balance_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Data do Saldo Inicial *</FormLabel>
                  <FormControl>
                    <Input
                      type="date"
                      {...field}
                      disabled={updateMutation.isPending || !isAdmin}
                    />
                  </FormControl>
                  <FormDescription>Data de referência do saldo inicial</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={formMethods.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Observações</FormLabel>
                  <FormControl>
                    <Textarea
                      rows={3}
                      placeholder="Notas adicionais..."
                      {...field}
                      disabled={updateMutation.isPending || !isAdmin}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {isAdmin && (
              <Button type="submit" disabled={updateMutation.isPending || !isAdmin}>
                {updateMutation.isPending ? 'Salvando...' : 'Salvar'}
              </Button>
            )}
          </form>
        </Form>
      </div>
    </div>
  );
}
