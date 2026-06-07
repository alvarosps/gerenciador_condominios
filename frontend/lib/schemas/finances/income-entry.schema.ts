import { z } from 'zod';
import { moneyField } from './money';

const condominiumSimpleSchema = z.object({
  id: z.number(),
  name: z.string(),
});

// The backend nests the FULL BuildingSerializer/CategorySerializer on read; we keep a deliberate
// subset here (Zod strips unknown keys) because the UI only consumes id/name (+ street_number/color).
const buildingSimpleSchema = z.object({
  id: z.number(),
  name: z.string(),
  street_number: z.number().optional(),
});

const categorySimpleSchema = z.object({
  id: z.number(),
  name: z.string(),
  color: z.string().optional().default(''),
});

export const incomeEntrySchema = z.object({
  id: z.number().optional(),
  condominium: condominiumSimpleSchema.optional(),
  building: buildingSimpleSchema.nullable().optional(),
  category: categorySimpleSchema.nullable().optional(),
  description: z.string().min(1, 'Descrição é obrigatória'),
  amount: moneyField,
  income_date: z.string(),
  is_received: z.boolean().default(false),
  received_date: z.string().nullable().optional(),
  notes: z.string().optional().default(''),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type IncomeEntry = z.infer<typeof incomeEntrySchema>;

export const incomeEntryWriteSchema = z.object({
  description: z.string().min(1, 'Descrição é obrigatória'),
  amount: z.number().min(0.01, 'Valor deve ser maior que zero'),
  income_date: z.string().min(1, 'Data é obrigatória'),
  is_received: z.boolean().default(false),
  received_date: z.string().nullable().optional(),
  building_id: z.number().nullable().optional(),
  category_id: z.number().nullable().optional(),
  notes: z.string().optional().default(''),
});

export type IncomeEntryWrite = z.infer<typeof incomeEntryWriteSchema>;

export interface IncomeEntryFilters {
  building_id?: number;
  category_id?: number;
  is_received?: boolean;
  date_from?: string;
  date_to?: string;
}
