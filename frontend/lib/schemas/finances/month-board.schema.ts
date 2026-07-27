import { z } from 'zod';
import { billSchema } from './bill.schema';

// Payload of GET finance-dashboard/month_board (S66) — a PLAIN object (not {results,count}):
// the interceptor does not unwrap it. `bills` in every section are serialized by BillSerializer,
// so we reuse billSchema (already carrying amount_is_estimated after S65/S71).
export const monthBoardGroupSchema = z.object({
  building_id: z.number().nullable(), // null = the "Condomínio" bucket (rendered last)
  building_label: z.string(),
  bills: z.array(billSchema),
});

export const monthBoardSchema = z.object({
  overdue: z.array(billSchema), // ACTIVE, remaining>0, due_date<today, ANY competence
  deferred_suspended: z.array(billSchema), // SUSPENDED/DEFERRED remaining>0, outside the totals
  groups: z.array(monthBoardGroupSchema), // ACTIVE bills of the month (paid included)
  totals: z.object({
    due: z.string(), // decimal strings — the display boundary converts (formatCurrency accepts)
    paid: z.string(),
    remaining: z.string(),
    overdue: z.string(), // Σ remaining of the overdue section (not part of due/paid/remaining)
  }),
  generation: z.object({ missing_count: z.number().int() }),
});

export type MonthBoard = z.infer<typeof monthBoardSchema>;
export type MonthBoardGroup = z.infer<typeof monthBoardGroupSchema>;
