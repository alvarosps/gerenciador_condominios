import { z } from 'zod';
import { buildingSchema } from './building.schema';
import { personSimpleSchema } from './credit-card.schema';
import { creditCardSchema } from './credit-card.schema';
import { expenseCategorySchema } from './expense-category.schema';
import { expenseInstallmentSchema } from './expense-installment.schema';
import {
  EXPENSE_TYPES,
  PERSON_REQUIRED_TYPES,
  BUILDING_REQUIRED_TYPES,
  type ExpenseType,
} from '@/lib/utils/expense-type-config';

const expenseBaseSchema = z.object({
  id: z.number().optional(),
  description: z.string().min(1, 'Descrição é obrigatória'),
  expense_type: z.enum(EXPENSE_TYPES, 'Tipo é obrigatório'),
  total_amount: z
    .string()
    .or(z.number())
    .transform((val) => Math.round(Number(val) * 100) / 100),
  expense_date: z.string(),
  person: personSimpleSchema.nullable().optional(),
  person_id: z.number().nullable().optional(),
  credit_card: creditCardSchema.nullable().optional(),
  credit_card_id: z.number().nullable().optional(),
  building: buildingSchema.nullable().optional(),
  building_id: z.number().nullable().optional(),
  category: expenseCategorySchema.nullable().optional(),
  category_id: z.number().nullable().optional(),
  is_installment: z.boolean().default(false),
  total_installments: z.number().nullable().optional(),
  is_debt_installment: z.boolean().default(false),
  is_offset: z.boolean().default(false),
  is_recurring: z.boolean().default(false),
  expected_monthly_amount: z
    .string()
    .or(z.number())
    .nullable()
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : null)),
  recurrence_day: z.number().nullable().optional(),
  is_paid: z.boolean().default(false),
  paid_date: z.string().nullable().optional(),
  end_date: z.string().nullable().optional(),
  bank_name: z.string().optional().default(''),
  interest_rate: z
    .string()
    .or(z.number())
    .nullable()
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : null)),
  notes: z.string().optional().default(''),
  installments: z.array(expenseInstallmentSchema).default([]),
  remaining_installments: z.number().optional(),
  total_paid: z
    .string()
    .or(z.number())
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : undefined)),
  total_remaining: z
    .string()
    .or(z.number())
    .optional()
    .transform((val) => (val !== null && val !== undefined ? Number(val) : undefined)),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

interface ExpenseValidationData {
  expense_type: string;
  person_id?: number | null;
  credit_card_id?: number | null;
  building_id?: number | null;
  is_installment: boolean;
  total_installments?: number | null;
}

export function validateExpenseRules(data: ExpenseValidationData, ctx: z.RefinementCtx): void {
  const type = data.expense_type;

  if (type === 'card_purchase') {
    if (!data.person_id) {
      ctx.addIssue({
        code: 'custom',
        message: 'Pessoa é obrigatória para compra no cartão',
        path: ['person_id'],
      });
    }
    if (!data.credit_card_id) {
      ctx.addIssue({
        code: 'custom',
        message: 'Cartão é obrigatório para compra no cartão',
        path: ['credit_card_id'],
      });
    }
  }

  if (
    PERSON_REQUIRED_TYPES.includes(type as ExpenseType) &&
    type !== 'card_purchase' &&
    !data.person_id
  ) {
    ctx.addIssue({
      code: 'custom',
      message: 'Pessoa é obrigatória para este tipo de empréstimo',
      path: ['person_id'],
    });
  }

  if (BUILDING_REQUIRED_TYPES.includes(type as ExpenseType) && !data.building_id) {
    ctx.addIssue({
      code: 'custom',
      message: 'Prédio é obrigatório para este tipo de despesa',
      path: ['building_id'],
    });
  }

  if (data.is_installment && (!data.total_installments || data.total_installments < 2)) {
    ctx.addIssue({
      code: 'custom',
      message: 'Número de parcelas deve ser pelo menos 2',
      path: ['total_installments'],
    });
  }
}

// Read schema: the API read shape omits the write-only *_id fields, so applying
// validateExpenseRules (which requires them) on read throws a ZodError that empties the whole
// list. Read hooks use this. The expense form applies validateExpenseRules to its OWN
// form-shaped schema (expense-form-modal.tsx), so there is intentionally no full read+refine
// schema exported here that a future read path could be accidentally wired to.
export const expenseReadSchema = expenseBaseSchema;

// superRefine does not change the output type, so Expense derives from the base read schema.
export type Expense = z.infer<typeof expenseBaseSchema>;
