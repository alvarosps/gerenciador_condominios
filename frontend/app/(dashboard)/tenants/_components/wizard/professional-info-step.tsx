'use client';

import { Briefcase } from 'lucide-react';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { StepProps, MARITAL_STATUS_OPTIONS } from './types';

export function ProfessionalInfoStep({ formMethods }: StepProps) {
  return (
    <div className="space-y-6">
      <FormField
        control={formMethods.control}
        name="profession"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Profissão *</FormLabel>
            <FormControl>
              <div className="relative">
                <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Ex: Engenheiro, Professor, Médico"
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
        name="marital_status"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Estado Civil *</FormLabel>
            <Select onValueChange={field.onChange} value={field.value}>
              <FormControl>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione o estado civil" />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                {MARITAL_STATUS_OPTIONS.map((status) => (
                  <SelectItem key={status} value={status}>
                    {status}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );
}
