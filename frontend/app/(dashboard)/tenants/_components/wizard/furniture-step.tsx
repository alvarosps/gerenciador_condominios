'use client';

import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Checkbox } from '@/components/ui/checkbox';
import { useFurniture } from '@/lib/api/hooks/use-furniture';
import { StepProps } from './types';

export function FurnitureStep({ formMethods }: StepProps) {
  const { data: furniture } = useFurniture();

  return (
    <div>
      <div className="mb-6">
        <h3 className="text-lg font-medium">Móveis do Inquilino</h3>
        <p className="text-sm text-muted-foreground">
          Selecione os móveis que o inquilino possui e levará para o apartamento (opcional)
        </p>
      </div>
      <FormField
        control={formMethods.control}
        name="furniture_ids"
        render={() => (
          <FormItem>
            <div className="grid grid-cols-2 gap-4">
              {furniture?.map((item) => (
                <FormField
                  key={item.id}
                  control={formMethods.control}
                  name="furniture_ids"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                      <FormControl>
                        <Checkbox
                          checked={field.value?.includes(item.id!)}
                          onCheckedChange={(checked) => {
                            const current = field.value || [];
                            if (checked) {
                              field.onChange([...current, item.id!]);
                            } else {
                              field.onChange(
                                current.filter((id) => id !== item.id)
                              );
                            }
                          }}
                        />
                      </FormControl>
                      <FormLabel className="font-normal cursor-pointer">
                        {item.name}
                      </FormLabel>
                    </FormItem>
                  )}
                />
              ))}
            </div>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );
}
