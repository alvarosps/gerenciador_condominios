import { z } from 'zod';
import { moneyField } from './money';

const condominiumSimpleSchema = z.object({
  id: z.number(),
  name: z.string(),
});

export const reserveSchema = z.object({
  id: z.number().optional(),
  condominium: condominiumSimpleSchema.optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
  notes: z.string().optional().default(''),
  balance: moneyField,
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type Reserve = z.infer<typeof reserveSchema>;

export const reserveWriteSchema = z.object({
  name: z.string().min(1, 'Nome é obrigatório'),
  notes: z.string().optional().default(''),
});

export type ReserveWrite = z.infer<typeof reserveWriteSchema>;

export const depositSchema = z.object({
  amount: z.number().min(0.01, 'Valor deve ser maior que zero'),
  movement_date: z.string().optional(),
  reference: z.string().optional(),
  notes: z.string().optional(),
});

export type DepositPayload = z.infer<typeof depositSchema>;

export const withdrawSchema = z.object({
  amount: z.number().min(0.01, 'Valor deve ser maior que zero'),
  movement_date: z.string().optional(),
});

export type WithdrawPayload = z.infer<typeof withdrawSchema>;
