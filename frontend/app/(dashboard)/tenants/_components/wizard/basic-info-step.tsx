'use client';

import { User } from 'lucide-react';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { formatCPFOrCNPJ } from '@/lib/utils/formatters';
import { StepProps } from './types';

export function BasicInfoStep({ formMethods }: StepProps) {
  return (
    <div className="space-y-6">
      <FormField
        control={formMethods.control}
        name="name"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Nome / Razão Social *</FormLabel>
            <FormControl>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Nome completo ou razão social"
                  className="pl-10"
                  {...field}
                />
              </div>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={formMethods.control}
        name="is_company"
        render={({ field }) => (
          <FormItem className="space-y-3">
            <FormLabel>Tipo de Pessoa *</FormLabel>
            <FormControl>
              <RadioGroup
                onValueChange={(value) => field.onChange(value === 'true')}
                value={String(field.value)}
                className="flex gap-4"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="false" id="person-false" />
                  <label
                    htmlFor="person-false"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                  >
                    Pessoa Física
                  </label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="true" id="person-true" />
                  <label
                    htmlFor="person-true"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                  >
                    Pessoa Jurídica
                  </label>
                </div>
              </RadioGroup>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={formMethods.control}
        name="cpf_cnpj"
        render={({ field }) => (
          <FormItem>
            <FormLabel>CPF / CNPJ *</FormLabel>
            <FormControl>
              <Input
                placeholder="000.000.000-00 ou 00.000.000/0000-00"
                maxLength={18}
                {...field}
                onChange={(e) => {
                  const formatted = formatCPFOrCNPJ(e.target.value);
                  field.onChange(formatted);
                }}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );
}
