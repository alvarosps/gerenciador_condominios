import { z } from 'zod';
import { billBehaviorValues } from '@/lib/schemas/finances/category.schema';

/**
 * Local form schema for the bill create/edit modal.
 *
 * Mirrors the writable Bill fields plus embedded line items (§4.1). The backend
 * (`create_with_lines`) is the authority for `amount_total`; the form's subtotal is a
 * display-only preview. Amounts must be >= 0 — an abatimento (offset) is a POSITIVE
 * amount with `is_offset=true`, never a negative number.
 */

export const billLineFormSchema = z.object({
  category_id: z.number().nullable(),
  description: z.string().min(1, 'Descrição é obrigatória'),
  amount: z.number().min(0, 'O valor não pode ser negativo'),
  is_offset: z.boolean(),
});

export const billFormSchema = z.object({
  description: z.string().min(1, 'Descrição é obrigatória'),
  building_id: z.number().nullable(),
  category_id: z.number().nullable(),
  competence_month: z.string().min(1, 'Competência é obrigatória'),
  due_date: z.string().min(1, 'Vencimento é obrigatório'),
  behavior: z.enum(billBehaviorValues),
  billing_account_id: z.number().nullable(),
  external_identifier: z.string(),
  issue_date: z.string().nullable(),
  notes: z.string(),
  line_items: z.array(billLineFormSchema).min(1, 'Adicione ao menos uma linha'),
});

export type BillFormValues = z.infer<typeof billFormSchema>;
export type BillLineFormValues = z.infer<typeof billLineFormSchema>;
