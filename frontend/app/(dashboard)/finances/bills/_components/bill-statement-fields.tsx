'use client';

import type { UseFormReturn } from 'react-hook-form';
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { BillAccountType, BillFormValues } from './bill-form-schema';

const SUPPLY_STATUS_LABELS = {
  active: 'Ligado',
  cut: 'Cortado',
} as const;

interface BillStatementFieldsProps {
  form: UseFormReturn<BillFormValues>;
  accountType: BillAccountType;
}

/**
 * Readings-only statement block, conditional on the selected `account_type`.
 *
 * Water → consumo_m3 / leituras / status; electricity → consumo_kwh / injeção /
 * leituras / classe / bandeira. Hidden for generic/iptu/internet. NO money fields —
 * the money is `BillLineItem`. In the manual flow the inputs render empty and editable;
 * the parser-draft prefill is S63. UI-only state (not part of the manual payload).
 */
export function BillStatementFields({ form, accountType }: BillStatementFieldsProps) {
  if (accountType === 'water') {
    return (
      <div className="space-y-4 rounded-md border p-4">
        <h3 className="text-sm font-medium">Leitura da conta de água</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="water_statement.consumo_m3"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Consumo (m³)</FormLabel>
                <FormControl>
                  <Input inputMode="numeric" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="water_statement.leitura_dias"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Dias de leitura</FormLabel>
                <FormControl>
                  <Input inputMode="numeric" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="water_statement.leitura_anterior"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Leitura anterior</FormLabel>
                <FormControl>
                  <Input inputMode="numeric" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="water_statement.leitura_atual"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Leitura atual</FormLabel>
                <FormControl>
                  <Input inputMode="numeric" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="water_statement.data_leitura"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Data da leitura</FormLabel>
                <FormControl>
                  <Input
                    type="date"
                    value={field.value ?? ''}
                    onChange={(e) => field.onChange(e.target.value || null)}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="water_statement.agua_status"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Água</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="active">{SUPPLY_STATUS_LABELS.active}</SelectItem>
                    <SelectItem value="cut">{SUPPLY_STATUS_LABELS.cut}</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="water_statement.esgoto_status"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Esgoto</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="active">{SUPPLY_STATUS_LABELS.active}</SelectItem>
                    <SelectItem value="cut">{SUPPLY_STATUS_LABELS.cut}</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
      </div>
    );
  }

  if (accountType === 'electricity') {
    return (
      <div className="space-y-4 rounded-md border p-4">
        <h3 className="text-sm font-medium">Leitura da conta de luz</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="electricity_statement.consumo_kwh"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Consumo (kWh)</FormLabel>
                <FormControl>
                  <Input inputMode="numeric" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="electricity_statement.energia_injetada_kwh"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Energia injetada (kWh)</FormLabel>
                <FormControl>
                  <Input inputMode="numeric" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="electricity_statement.leitura_anterior"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Leitura anterior</FormLabel>
                <FormControl>
                  <Input inputMode="numeric" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="electricity_statement.leitura_atual"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Leitura atual</FormLabel>
                <FormControl>
                  <Input inputMode="numeric" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="electricity_statement.leitura_dias"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Dias de leitura</FormLabel>
                <FormControl>
                  <Input inputMode="numeric" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="electricity_statement.classe"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Classe</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="electricity_statement.bandeira"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Bandeira</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
      </div>
    );
  }

  return null;
}
