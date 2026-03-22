'use client';

import { useState } from 'react';
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
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import {
  useCreateCreditCard,
  useDeleteCreditCard,
} from '@/lib/api/hooks/use-credit-cards';
import { type CreditCard } from '@/lib/schemas/credit-card.schema';

interface CreditCardSectionProps {
  personId: number;
  creditCards: CreditCard[];
}

const cardFormSchema = z.object({
  nickname: z.string().min(1, 'Apelido é obrigatório'),
  last_four_digits: z
    .string()
    .min(4, 'Deve ter 4 dígitos')
    .max(4, 'Deve ter 4 dígitos')
    .regex(/^\d{4}$/, 'Deve conter apenas números'),
  closing_day: z.number().min(1, 'Mín. 1').max(31, 'Máx. 31'),
  due_day: z.number().min(1, 'Mín. 1').max(31, 'Máx. 31'),
});

type CardFormValues = z.infer<typeof cardFormSchema>;

export function CreditCardSection({ personId, creditCards }: CreditCardSectionProps) {
  const [isAdding, setIsAdding] = useState(false);
  const createMutation = useCreateCreditCard();
  const deleteMutation = useDeleteCreditCard();

  const formMethods = useForm<CardFormValues>({
    resolver: zodResolver(cardFormSchema),
    defaultValues: {
      nickname: '',
      last_four_digits: '',
      closing_day: 1,
      due_day: 1,
    },
  });

  const onSubmit = async (values: CardFormValues) => {
    try {
      await createMutation.mutateAsync({
        ...values,
        person_id: personId,
        is_active: true,
      });
      toast.success('Cartão adicionado com sucesso');
      formMethods.reset();
      setIsAdding(false);
    } catch (error) {
      toast.error('Erro ao adicionar cartão');
      console.error('Create card error:', error);
    }
  };

  const handleDeleteCard = async (cardId: number) => {
    try {
      await deleteMutation.mutateAsync(cardId);
      toast.success('Cartão removido com sucesso');
    } catch (error) {
      toast.error('Erro ao remover cartão');
      console.error('Delete card error:', error);
    }
  };

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-medium">Cartões de Crédito</h4>
        {!isAdding && (
          <Button type="button" variant="outline" size="sm" onClick={() => setIsAdding(true)}>
            <Plus className="h-4 w-4 mr-1" />
            Adicionar Cartão
          </Button>
        )}
      </div>

      {creditCards.length > 0 && (
        <div className="space-y-2">
          {creditCards.map((card) => (
            <div key={card.id} className="flex items-center justify-between bg-muted/50 rounded px-3 py-2">
              <div className="flex items-center gap-3">
                <span className="font-medium">{card.nickname}</span>
                <span className="text-muted-foreground">•••• {card.last_four_digits}</span>
                <span className="text-sm text-muted-foreground">
                  Fecha dia {card.closing_day} | Vence dia {card.due_day}
                </span>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (card.id !== undefined) void handleDeleteCard(card.id);
                }}
                disabled={deleteMutation.isPending}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {creditCards.length === 0 && !isAdding && (
        <p className="text-sm text-muted-foreground">Nenhum cartão cadastrado</p>
      )}

      {isAdding && (
        <Form {...formMethods}>
          <form onSubmit={formMethods.handleSubmit(onSubmit)} className="space-y-3 border-t pt-3">
            <div className="grid grid-cols-2 gap-3">
              <FormField
                control={formMethods.control}
                name="nickname"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Apelido *</FormLabel>
                    <FormControl>
                      <Input placeholder="Ex: Nubank" {...field} disabled={createMutation.isPending} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={formMethods.control}
                name="last_four_digits"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Últimos 4 dígitos *</FormLabel>
                    <FormControl>
                      <Input placeholder="1234" maxLength={4} {...field} disabled={createMutation.isPending} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <FormField
                control={formMethods.control}
                name="closing_day"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Dia de Fechamento *</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={1}
                        max={31}
                        {...field}
                        value={field.value}
                        onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : 1)}
                        disabled={createMutation.isPending}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={formMethods.control}
                name="due_day"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Dia de Vencimento *</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={1}
                        max={31}
                        {...field}
                        value={field.value}
                        onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : 1)}
                        disabled={createMutation.isPending}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit" size="sm" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Salvando...' : 'Salvar Cartão'}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsAdding(false);
                  formMethods.reset();
                }}
                disabled={createMutation.isPending}
              >
                Cancelar
              </Button>
            </div>
          </form>
        </Form>
      )}
    </div>
  );
}
