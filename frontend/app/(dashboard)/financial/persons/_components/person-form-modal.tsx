'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
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
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import {
  useCreatePerson,
  useUpdatePerson,
} from '@/lib/api/hooks/use-persons';
import { type Person } from '@/lib/schemas/person.schema';
import { CreditCardSection } from './credit-card-section';

interface PersonFormModalProps {
  open: boolean;
  person?: Person | null;
  onClose: () => void;
}

const RELATIONSHIP_OPTIONS = [
  { value: 'Filho', label: 'Filho' },
  { value: 'Genro', label: 'Genro' },
  { value: 'Funcionária', label: 'Funcionária' },
  { value: 'Outro', label: 'Outro' },
];

const personFormSchema = z.object({
  name: z.string().min(1, 'Nome é obrigatório'),
  relationship: z.string().min(1, 'Relação é obrigatória'),
  phone: z.string(),
  email: z.string(),
  is_owner: z.boolean(),
  is_employee: z.boolean(),
  notes: z.string(),
});

type PersonFormValues = z.infer<typeof personFormSchema>;

export function PersonFormModal({ open, person, onClose }: PersonFormModalProps) {
  const createMutation = useCreatePerson();
  const updateMutation = useUpdatePerson();

  const isEditing = Boolean(person?.id);
  const isLoading = createMutation.isPending || updateMutation.isPending;

  const formMethods = useForm<PersonFormValues>({
    resolver: zodResolver(personFormSchema),
    defaultValues: {
      name: '',
      relationship: '',
      phone: '',
      email: '',
      is_owner: false,
      is_employee: false,
      notes: '',
    },
  });

  useEffect(() => {
    if (person) {
      formMethods.reset({
        name: person.name,
        relationship: person.relationship,
        phone: person.phone ?? '',
        email: person.email ?? '',
        is_owner: person.is_owner,
        is_employee: person.is_employee,
        notes: person.notes ?? '',
      });
    } else {
      formMethods.reset({
        name: '',
        relationship: '',
        phone: '',
        email: '',
        is_owner: false,
        is_employee: false,
        notes: '',
      });
    }
  }, [person, formMethods]);

  const onSubmit = async (values: PersonFormValues) => {
    try {
      if (isEditing && person?.id) {
        await updateMutation.mutateAsync({ ...values, id: person.id });
        toast.success('Pessoa atualizada com sucesso');
      } else {
        await createMutation.mutateAsync(values);
        toast.success('Pessoa criada com sucesso');
      }

      onClose();
      formMethods.reset();
    } catch (error) {
      toast.error('Erro ao salvar pessoa');
      console.error('Save error:', error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Editar Pessoa' : 'Nova Pessoa'}</DialogTitle>
        </DialogHeader>

        <Form {...formMethods}>
          <form onSubmit={formMethods.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={formMethods.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nome *</FormLabel>
                  <FormControl>
                    <Input placeholder="Nome completo" maxLength={200} {...field} disabled={isLoading} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={formMethods.control}
              name="relationship"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Relação *</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    value={field.value}
                    disabled={isLoading}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione a relação" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {RELATIONSHIP_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={formMethods.control}
                name="phone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Telefone</FormLabel>
                    <FormControl>
                      <Input placeholder="(11) 99999-9999" {...field} disabled={isLoading} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={formMethods.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" placeholder="email@exemplo.com" {...field} disabled={isLoading} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={formMethods.control}
                name="is_owner"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between rounded-lg border p-3">
                    <FormLabel className="cursor-pointer">Proprietário</FormLabel>
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                        disabled={isLoading}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />

              <FormField
                control={formMethods.control}
                name="is_employee"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between rounded-lg border p-3">
                    <FormLabel className="cursor-pointer">Funcionário</FormLabel>
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                        disabled={isLoading}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={formMethods.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Observações</FormLabel>
                  <FormControl>
                    <Textarea
                      rows={2}
                      placeholder="Notas adicionais..."
                      {...field}
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {isEditing && person?.id && (
              <CreditCardSection
                personId={person.id}
                creditCards={person.credit_cards ?? []}
              />
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isEditing ? 'Atualizar' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
