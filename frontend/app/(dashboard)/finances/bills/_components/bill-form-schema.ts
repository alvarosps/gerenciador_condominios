import { z } from 'zod';
import { billBehaviorValues } from '@/lib/schemas/finances/category.schema';

/**
 * Local form schema for the bill create/edit modal.
 *
 * Mirrors the writable Bill fields plus embedded line items (§4.1). The backend
 * (`create_with_lines`) is the authority for `amount_total`; the form's subtotal is a
 * display-only preview. Amounts must be >= 0 — an abatimento (offset) is a POSITIVE
 * amount with `is_offset=true`, never a negative number.
 *
 * `account_type` and the `*_statement` blocks are UI-only state that drives the
 * conditional readings-only statement panel (water/electricity). They are NOT part of
 * the create/update payload in the manual flow — S63 wires the parser draft prefill and
 * the statement persistence (`create_with_lines`/`update_with_lines`). The API contract
 * (`bill.schema.ts`) is unchanged here.
 */

export const billLineFormSchema = z.object({
  category_id: z.number().nullable(),
  description: z.string().min(1, 'Descrição é obrigatória'),
  amount: z.number().min(0, 'O valor não pode ser negativo'),
  is_offset: z.boolean(),
  // Set only by the parser-draft prefill (S63): a line reconciled to an embedded Installment.
  // Such a line is rendered locked (read-only) — the admin does not edit the reconciliation.
  installment_id: z.number().nullable(),
});

export const billAccountTypeValues = [
  'generic',
  'water',
  'electricity',
  'iptu',
  'internet',
] as const;

export const supplyStatusValues = ['active', 'cut'] as const;

export const waterStatementFormSchema = z.object({
  consumo_m3: z.string(),
  leitura_anterior: z.string(),
  leitura_atual: z.string(),
  leitura_dias: z.string(),
  data_leitura: z.string().nullable(),
  agua_status: z.enum(supplyStatusValues),
  esgoto_status: z.enum(supplyStatusValues),
});

export const electricityStatementFormSchema = z.object({
  consumo_kwh: z.string(),
  energia_injetada_kwh: z.string(),
  leitura_anterior: z.string(),
  leitura_atual: z.string(),
  leitura_dias: z.string(),
  classe: z.string(),
  bandeira: z.string(),
});

export const billFormSchema = z.object({
  description: z.string().min(1, 'Descrição é obrigatória'),
  building_id: z.number().nullable(),
  category_id: z.number().nullable(),
  competence_month: z.string().min(1, 'Competência é obrigatória'),
  due_date: z.string().min(1, 'Vencimento é obrigatório'),
  behavior: z.enum(billBehaviorValues),
  account_type: z.enum(billAccountTypeValues),
  billing_account_id: z.number().nullable(),
  external_identifier: z.string(),
  issue_date: z.string().nullable(),
  notes: z.string(),
  water_statement: waterStatementFormSchema,
  electricity_statement: electricityStatementFormSchema,
  line_items: z.array(billLineFormSchema).min(1, 'Adicione ao menos uma linha'),
});

export type BillFormValues = z.infer<typeof billFormSchema>;
export type BillLineFormValues = z.infer<typeof billLineFormSchema>;
export type BillAccountType = (typeof billAccountTypeValues)[number];
