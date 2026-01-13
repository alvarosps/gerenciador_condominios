'use client';

import { useFieldArray, UseFormReturn } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Plus, Trash2, User, Phone } from 'lucide-react';
import { formatBrazilianPhone } from '@/lib/utils/formatters';

interface TenantFormValues {
  name: string;
  cpf_cnpj: string;
  is_company: boolean;
  phone: string;
  email?: string;
  phone_alternate?: string;
  profession: string;
  marital_status: string;
  dependents?: Array<{
    name: string;
    phone: string;
  }>;
  furniture_ids?: number[];
  deposit_amount?: number | null;
  cleaning_fee_paid?: boolean;
  tag_deposit_paid?: boolean;
  rent_due_day?: number;
}

interface Props {
  formMethods: UseFormReturn<TenantFormValues>;
}

export function DependentFormList({ formMethods }: Props) {
  const { fields, append, remove } = useFieldArray({
    control: formMethods.control,
    name: 'dependents',
  });

  return (
    <>
      {fields.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 border-2 border-dashed rounded-lg">
          <p className="text-sm text-muted-foreground mb-4">
            Nenhum dependente adicionado
          </p>
          <Button
            type="button"
            onClick={() => append({ name: '', phone: '' })}
          >
            <Plus className="h-4 w-4 mr-2" />
            Adicionar Primeiro Dependente
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {fields.map((field, index) => (
            <Card key={field.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">
                    Dependente {index + 1}
                  </CardTitle>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => remove(index)}
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Remover
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <FormField
                  control={formMethods.control}
                  name={`dependents.${index}.name`}
                  render={({ field: formField }) => (
                    <FormItem>
                      <FormLabel>Nome do Dependente</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                          <Input
                            placeholder="Nome completo"
                            className="pl-10"
                            {...formField}
                          />
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={formMethods.control}
                  name={`dependents.${index}.phone`}
                  render={({ field: formField }) => (
                    <FormItem>
                      <FormLabel>Telefone do Dependente</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                          <Input
                            placeholder="(00) 00000-0000"
                            maxLength={15}
                            className="pl-10"
                            {...formField}
                            onChange={(e) => {
                              const formatted = formatBrazilianPhone(e.target.value);
                              formField.onChange(formatted);
                            }}
                          />
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </CardContent>
            </Card>
          ))}

          <Button
            type="button"
            variant="outline"
            onClick={() => append({ name: '', phone: '' })}
            className="w-full"
          >
            <Plus className="h-4 w-4 mr-2" />
            Adicionar Outro Dependente
          </Button>
        </div>
      )}
    </>
  );
}
