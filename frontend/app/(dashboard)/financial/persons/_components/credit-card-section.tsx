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
import { Plus, Trash2, Pencil } from 'lucide-react';
import { toast } from 'sonner';
import {
  useCreateCreditCard,
  useUpdateCreditCard,
  useDeleteCreditCard,
} from '@/lib/api/hooks/use-credit-cards';
import { type CreditCard } from '@/lib/schemas/credit-card.schema';

interface CreditCardSectionProps {
  personId: number;
  creditCards: CreditCard[];
}

const cardFormSchema = z.object({
  nickname: z.string().min(1, 'Apelido é obrigatório'),
  last_four_digits: z.string().max(4, 'Máximo 4 dígitos'),
  closing_day: z.number().min(1, 'Mín. 1').max(31, 'Máx. 31'),
  due_day: z.number().min(1, 'Mín. 1').max(31, 'Máx. 31'),
});

type CardFormValues = z.infer<typeof cardFormSchema>;

export function CreditCardSection({ personId, creditCards }: CreditCardSectionProps) {
  const [editingCardId, setEditingCardId] = useState<number | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const createMutation = useCreateCreditCard();
  const updateMutation = useUpdateCreditCard();
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

  const isSaving = createMutation.isPending || updateMutation.isPending;

  const startEditing = (card: CreditCard) => {
    setIsAdding(false);
    setEditingCardId(card.id ?? null);
    formMethods.reset({
      nickname: card.nickname,
      last_four_digits: card.last_four_digits ?? '',
      closing_day: card.closing_day,
      due_day: card.due_day,
    });
  };

  const startAdding = () => {
    setEditingCardId(null);
    setIsAdding(true);
    formMethods.reset({
      nickname: '',
      last_four_digits: '',
      closing_day: 1,
      due_day: 1,
    });
  };

  const cancelForm = () => {
    setIsAdding(false);
    setEditingCardId(null);
    formMethods.reset();
  };

  const onSubmit = async (values: CardFormValues) => {
    try {
      if (editingCardId) {
        await updateMutation.mutateAsync({
          ...values,
          id: editingCardId,
          person_id: personId,
          is_active: true,
        });
        toast.success('Cartão atualizado com sucesso');
      } else {
        await createMutation.mutateAsync({
          ...values,
          person_id: personId,
          is_active: true,
        });
        toast.success('Cartão adicionado com sucesso');
      }
      cancelForm();
    } catch {
      toast.error(editingCardId ? 'Erro ao atualizar cartão' : 'Erro ao adicionar cartão');
    }
  };

  const handleDeleteCard = async (cardId: number) => {
    try {
      await deleteMutation.mutateAsync(cardId);
      toast.success('Cartão removido com sucesso');
    } catch {
      toast.error('Erro ao remover cartão');
    }
  };

  const isFormOpen = isAdding || editingCardId !== null;

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-medium">Cartões de Crédito</h4>
        {!isFormOpen && (
          <Button type="button" variant="outline" size="sm" onClick={startAdding}>
            <Plus className="h-4 w-4 mr-1" />
            Adicionar Cartão
          </Button>
        )}
      </div>

      {creditCards.length > 0 && (
        <div className="space-y-2">
          {creditCards.map((card) => (
            <div
              key={card.id}
              className={`flex items-center justify-between rounded px-3 py-2 ${
                editingCardId === card.id ? 'bg-blue-50 border border-blue-200' : 'bg-muted/50'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="font-medium">{card.nickname}</span>
                {card.last_four_digits && (
                  <span className="text-muted-foreground">•••• {card.last_four_digits}</span>
                )}
                <span className="text-sm text-muted-foreground">
                  Fecha dia {card.closing_day} | Vence dia {card.due_day}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => startEditing(card)}
                  disabled={isSaving || deleteMutation.isPending}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    if (card.id !== undefined) void handleDeleteCard(card.id);
                  }}
                  disabled={deleteMutation.isPending || isSaving}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {creditCards.length === 0 && !isFormOpen && (
        <p className="text-sm text-muted-foreground">Nenhum cartão cadastrado</p>
      )}

      {isFormOpen && (
        <Form {...formMethods}>
          <form onSubmit={formMethods.handleSubmit(onSubmit)} className="space-y-3 border-t pt-3">
            <p className="text-sm font-medium text-muted-foreground">
              {editingCardId ? 'Editando cartão' : 'Novo cartão'}
            </p>
            <div className="grid grid-cols-2 gap-3">
              <FormField
                control={formMethods.control}
                name="nickname"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Apelido *</FormLabel>
                    <FormControl>
                      <Input placeholder="Ex: Nubank" {...field} disabled={isSaving} />
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
                    <FormLabel>Últimos 4 dígitos</FormLabel>
                    <FormControl>
                      <Input placeholder="1234" maxLength={4} {...field} disabled={isSaving} />
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
                        disabled={isSaving}
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
                        disabled={isSaving}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit" size="sm" disabled={isSaving}>
                {isSaving ? 'Salvando...' : editingCardId ? 'Atualizar' : 'Salvar Cartão'}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={cancelForm}
                disabled={isSaving}
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
