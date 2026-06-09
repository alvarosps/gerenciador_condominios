'use client';

import { useFieldArray, type UseFormReturn } from 'react-hook-form';
import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useFinanceCategories } from '@/lib/api/hooks/use-finance-categories';
import { formatCurrency } from '@/lib/utils/formatters';
import { computeLineTotal } from '@/lib/utils/finances';
import type { BillFormValues } from './bill-form-schema';

const NO_CATEGORY = 'none';

interface BillLineItemsFieldProps {
  form: UseFormReturn<BillFormValues>;
}

export function BillLineItemsField({ form }: BillLineItemsFieldProps) {
  const { fields, append, remove } = useFieldArray({ control: form.control, name: 'line_items' });
  const { data: categories } = useFinanceCategories();

  const lines = form.watch('line_items');
  const subtotal = computeLineTotal(lines ?? []);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <FormLabel>Linhas</FormLabel>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() =>
            append({
              category_id: null,
              description: '',
              amount: 0,
              is_offset: false,
              installment_id: null,
            })
          }
        >
          <Plus className="mr-1 h-4 w-4" />
          Adicionar linha
        </Button>
      </div>

      {fields.length === 0 ? (
        <p className="rounded-md border-2 border-dashed py-6 text-center text-sm text-muted-foreground">
          Nenhuma linha — adicione consumo e/ou parcela
        </p>
      ) : (
        <div className="space-y-3">
          {fields.map((field, index) => {
            const installmentId = lines?.[index]?.installment_id ?? null;
            const isLocked = installmentId !== null;
            return (
            <div key={field.id} className="rounded-md border p-3">
              <div className="flex items-start justify-between gap-2">
                <span className="text-sm font-medium">
                  Linha {index + 1}
                  {isLocked && (
                    <span className="ml-2 text-xs font-normal text-muted-foreground">
                      (parcela reconciliada)
                    </span>
                  )}
                </span>
                {!isLocked && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => remove(index)}
                    aria-label={`Remover linha ${String(index + 1)}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>

              <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name={`line_items.${index}.description`}
                  render={({ field: lineField }) => (
                    <FormItem className="sm:col-span-2">
                      <FormLabel>Descrição</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Ex: Consumo de energia"
                          disabled={isLocked}
                          {...lineField}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name={`line_items.${index}.category_id`}
                  render={({ field: lineField }) => (
                    <FormItem>
                      <FormLabel>Categoria (opcional)</FormLabel>
                      <Select
                        value={lineField.value ? String(lineField.value) : NO_CATEGORY}
                        onValueChange={(value) =>
                          lineField.onChange(value === NO_CATEGORY ? null : Number(value))
                        }
                        disabled={isLocked}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Selecione" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value={NO_CATEGORY}>Nenhuma</SelectItem>
                          {categories?.map((category) =>
                            category.id === undefined ? null : (
                              <SelectItem key={category.id} value={String(category.id)}>
                                {category.name}
                              </SelectItem>
                            ),
                          )}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name={`line_items.${index}.amount`}
                  render={({ field: lineField }) => (
                    <FormItem>
                      <FormLabel>Valor</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                            R$
                          </span>
                          <Input
                            type="number"
                            min={0}
                            step="0.01"
                            placeholder="0,00"
                            className="pl-10"
                            disabled={isLocked}
                            value={Number.isNaN(lineField.value) ? '' : lineField.value}
                            onChange={(e) => {
                              lineField.onChange(e.target.value === '' ? 0 : Number(e.target.value));
                            }}
                          />
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name={`line_items.${index}.is_offset`}
                  render={({ field: lineField }) => (
                    <FormItem className="flex items-center justify-between sm:col-span-2">
                      <FormLabel>Abatimento (valor subtraído do total)</FormLabel>
                      <FormControl>
                        <Switch
                          checked={lineField.value}
                          onCheckedChange={lineField.onChange}
                          disabled={isLocked}
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>
            </div>
            );
          })}
        </div>
      )}

      <div className="flex items-center justify-between border-t pt-3">
        <span className="text-sm font-medium text-muted-foreground">Subtotal (prévia)</span>
        <span className="text-base font-semibold" data-testid="bill-line-subtotal">
          {formatCurrency(subtotal)}
        </span>
      </div>
    </div>
  );
}
