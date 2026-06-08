import { z } from 'zod';
import { moneyField } from './money';

export const RESERVE_MOVEMENT_KINDS = ['deposit', 'withdrawal'] as const;
export type ReserveMovementKind = (typeof RESERVE_MOVEMENT_KINDS)[number];

const reserveSimpleSchema = z.object({
  id: z.number(),
  name: z.string(),
});

export const reserveMovementSchema = z.object({
  id: z.number().optional(),
  reserve: reserveSimpleSchema.optional(),
  kind: z.enum(RESERVE_MOVEMENT_KINDS),
  amount: moneyField,
  movement_date: z.string(),
  bill: z.number().nullable().optional(),
  reference: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type ReserveMovement = z.infer<typeof reserveMovementSchema>;

export interface ReserveMovementFilters {
  reserve_id?: number;
  kind?: ReserveMovementKind;
  date_from?: string;
  date_to?: string;
}
