import { z } from 'zod';
import { personSimpleSchema } from '../credit-card.schema';
import { condominiumRefSchema, moneyField } from './money';

/**
 * Six month statuses, not five (S79). `empty` is a month inside the window with NO movement at
 * all — the window materializes gaps so the statement has no holes. Rendering it as "Quitado"
 * was a real backend bug (it read as "that month was settled" between two overdue months), so it
 * gets its own neutral label/tone here and must NEVER borrow the success styling of `paid`.
 */
export const thirdPartyMonthStatusValues = [
  'paid',
  'overdue',
  'partially_paid',
  'open',
  'credit',
  'empty',
] as const;
export const thirdPartyMonthStatusEnum = z.enum(thirdPartyMonthStatusValues);
export type ThirdPartyMonthStatus = z.infer<typeof thirdPartyMonthStatusEnum>;

export const THIRD_PARTY_MONTH_STATUS_LABELS: Record<ThirdPartyMonthStatus, string> = {
  paid: 'Quitado',
  overdue: 'Atrasado',
  partially_paid: 'Parcial',
  open: 'Em aberto',
  credit: 'Crédito',
  empty: 'Sem movimento',
};

export const thirdPartyItemKindValues = ['payment', 'purchase', 'settlement'] as const;
export const thirdPartyItemKindEnum = z.enum(thirdPartyItemKindValues);
export type ThirdPartyItemKind = z.infer<typeof thirdPartyItemKindEnum>;

export const THIRD_PARTY_ITEM_KIND_LABELS: Record<ThirdPartyItemKind, string> = {
  payment: 'Pagamento',
  purchase: 'Compra',
  // The repayment side: what the owners already handed over. Listed in the month it was paid —
  // it is the counterpart of `devido`, never part of it.
  settlement: 'Acerto',
};

/**
 * One row composing a month: a bill the person paid, a purchase she made (both make up `devido`),
 * or an acerto the owners paid her (the counterpart, so `aplicado` is auditable).
 */
export const thirdPartyStatementItemSchema = z.object({
  kind: thirdPartyItemKindEnum,
  id: z.number(),
  description: z.string(),
  amount: moneyField, // decimal string on the wire; Number only at this boundary
  date: z.string(), // YYYY-MM-DD
});

export const thirdPartyStatementMonthSchema = z.object({
  month: z.string(), // YYYY-MM-01
  devido: moneyField,
  aplicado: moneyField,
  resto: moneyField,
  status: thirdPartyMonthStatusEnum,
  items: z.array(thirdPartyStatementItemSchema).default([]),
});

/** Totals are read from the backend and NEVER recomputed here (design §6.5 / S50 discipline). */
export const thirdPartyStatementTotalsSchema = z.object({
  total_devido: moneyField,
  total_pago: moneyField,
  total_em_aberto: moneyField,
  total_atrasado: moneyField,
  saldo_credor: moneyField,
});

/** GET /finances/third-party/statement/?person_id= — a PLAIN object (not {results,count}). */
export const thirdPartyStatementSchema = z.object({
  person_id: z.number(),
  person_name: z.string(),
  months: z.array(thirdPartyStatementMonthSchema).default([]),
  totals: thirdPartyStatementTotalsSchema,
});

/** GET /finances/third-party/people/ — a PLAIN array; whoever owes nothing is omitted. */
export const thirdPartyPersonSchema = z.object({
  person_id: z.number(),
  person_name: z.string(),
  total_em_aberto: moneyField,
  total_atrasado: moneyField,
  last_settlement_date: z.string().nullable(),
});

export const thirdPartySettlementSchema = z
  .object({
    id: z.number().optional(),
    condominium: condominiumRefSchema.optional(),
    condominium_id: z.number().optional(), // write-only on the serializer (defaulted by the API)
    person: personSimpleSchema.optional(), // nested read (PersonSimpleSerializer)
    person_id: z.number().optional(), // write
    settlement_date: z.string(), // YYYY-MM-DD
    amount: moneyField, // decimal string; > 0 enforced by the backend AND by the form schema
    method: z.string().optional().default(''),
    notes: z.string().optional().default(''),
    created_at: z.string().optional(),
    updated_at: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    // A settlement always has somebody on the other side. On WRITE the form supplies `person_id`;
    // on READ the API returns only the nested `person` object (`person_id` is write_only).
    // Requiring the id alone would throw on every read parse and empty the whole list — the
    // registered trap (installment-plan.schema.ts:45-55).
    const hasPerson =
      (data.person_id !== null && data.person_id !== undefined) ||
      (data.person !== null && data.person !== undefined);
    if (!hasPerson) {
      ctx.addIssue({
        code: 'custom',
        path: ['person_id'],
        message: 'Pessoa é obrigatória',
      });
    }
  });

export type ThirdPartyStatement = z.infer<typeof thirdPartyStatementSchema>;
export type ThirdPartyStatementMonth = z.infer<typeof thirdPartyStatementMonthSchema>;
export type ThirdPartyStatementItem = z.infer<typeof thirdPartyStatementItemSchema>;
export type ThirdPartyPerson = z.infer<typeof thirdPartyPersonSchema>;
export type ThirdPartySettlement = z.infer<typeof thirdPartySettlementSchema>;
