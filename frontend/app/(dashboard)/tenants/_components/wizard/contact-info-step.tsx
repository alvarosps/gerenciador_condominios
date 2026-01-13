'use client';

import { Phone } from 'lucide-react';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { formatBrazilianPhone } from '@/lib/utils/formatters';
import { StepProps } from './types';

export function ContactInfoStep({ formMethods }: StepProps) {
  return (
    <div className="space-y-6">
      <FormField
        control={formMethods.control}
        name="phone"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Telefone Principal *</FormLabel>
            <FormControl>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="(00) 00000-0000"
                  maxLength={15}
                  className="pl-10"
                  {...field}
                  onChange={(e) => {
                    const formatted = formatBrazilianPhone(e.target.value);
                    field.onChange(formatted);
                  }}
                />
              </div>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={formMethods.control}
        name="phone_alternate"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Telefone Alternativo (opcional)</FormLabel>
            <FormControl>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="(00) 00000-0000"
                  maxLength={15}
                  className="pl-10"
                  {...field}
                  onChange={(e) => {
                    const formatted = formatBrazilianPhone(e.target.value);
                    field.onChange(formatted);
                  }}
                />
              </div>
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
            <FormLabel>Email (opcional)</FormLabel>
            <FormControl>
              <Input
                type="email"
                placeholder="email@exemplo.com"
                {...field}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );
}
