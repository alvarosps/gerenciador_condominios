import { z } from 'zod';
import {
  billLineItemSchema,
  electricityStatementSchema,
  waterStatementSchema,
} from './bill.schema';
import { billingAccountSchema } from './billing-account.schema';

/**
 * The serialized invoice DRAFT returned by `POST /api/finances/bills/parse_invoice/`
 * (InvoiceDraftService.build_draft, S60). NOT the internal `ParsedLine` of the S59 parser —
 * the draft line is already reconciled: it carries `installment_id` (already resolved) and
 * `category_id`, NEVER `installment_number`. The response is a single object (not {results,count})
 * so the client interceptor leaves it untouched (design §8.2).
 */

export const parsedLineSchema = billLineItemSchema.extend({
  category_id: z.number().nullable().optional(),
  installment_id: z.number().nullable().optional(),
});

export const parsedInvoiceSchema = z.object({
  bill: z.object({
    competence_month: z.string(),
    due_date: z.string(),
    external_identifier: z.string().default(''),
    behavior: z.string(),
    account_type: z.string().optional(),
    building_id: z.number().nullable().optional(), // herdado da conta casada (S60)
    category_id: z.number().nullable().optional(), // herdado da conta casada (S60)
    description: z.string(), // S60 build_draft: nome da conta casada, senão "{tipo} {MM/YYYY}"
  }),
  line_items: z.array(parsedLineSchema),
  statement: z.union([waterStatementSchema, electricityStatementSchema]).nullable(),
  matched_account: billingAccountSchema.nullable(),
  existing_bill_id: z.number().nullable().optional(), // truthy → roteia para update_with_lines (S60)
  warnings: z.array(z.string()).default([]),
});

export type ParsedInvoice = z.infer<typeof parsedInvoiceSchema>;
export type ParsedLine = z.infer<typeof parsedLineSchema>;
