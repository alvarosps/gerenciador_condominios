import { z } from 'zod';

interface RawExpenseCategory {
  id?: number;
  name: string;
  description?: string;
  color?: string;
  parent?: RawExpenseCategory | null;
  parent_id?: number | null;
  subcategories?: RawExpenseCategory[];
  created_at?: string;
  updated_at?: string;
}

export const expenseCategorySchema: z.ZodType<RawExpenseCategory> = z.lazy(() =>
  z.object({
    id: z.number().optional(),
    name: z.string().min(1, 'Nome é obrigatório'),
    description: z.string().optional().default(''),
    color: z.string().optional().default('#6B7280'),
    parent: expenseCategorySchema.nullable().optional(),
    parent_id: z.number().nullable().optional(),
    subcategories: z.array(expenseCategorySchema).default([]),
    created_at: z.string().optional(),
    updated_at: z.string().optional(),
  }),
);

export type ExpenseCategory = z.infer<typeof expenseCategorySchema>;
