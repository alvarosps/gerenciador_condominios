import { describe, it, expect } from 'vitest';
import { ZodError } from 'zod';
import { installmentPlanSchema } from '../installment-plan.schema';
import { createMockBillingAccount } from '@/tests/mocks/data/finances';

/**
 * The embedded superRefine must accept EITHER the write `billing_account_id` OR the read-only
 * nested `billing_account` (the serializer emits the nested object and omits the write_only id on
 * READ). It must still reject an embedded plan linked to NEITHER. These tests pin that guard so a
 * future over-relaxation (which would re-empty the Parcelas list, or silently allow an unlinked
 * embedded plan) is caught.
 */
function basePlan(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    description: 'Parcelamento DMAE água 836',
    total_amount: '4346.08',
    installment_count: 46,
    start_due_date: '2026-06-04',
    default_due_day: 4,
    lifecycle_state: 'active',
    embedded: true,
    installments: [],
    notes: '',
    ...overrides,
  };
}

describe('installmentPlanSchema embedded linkage', () => {
  it('accepts an embedded plan from a READ payload (nested billing_account, no billing_account_id)', () => {
    const parsed = installmentPlanSchema.parse(
      basePlan({ billing_account: createMockBillingAccount({ id: 9, account_type: 'water' }) }),
    );
    expect(parsed.embedded).toBe(true);
    expect(parsed.billing_account?.account_type).toBe('water');
  });

  it('accepts an embedded plan from a WRITE payload (billing_account_id, no nested object)', () => {
    const parsed = installmentPlanSchema.parse(basePlan({ billing_account_id: 9 }));
    expect(parsed.billing_account_id).toBe(9);
  });

  it('rejects an embedded plan linked to NEITHER billing_account nor billing_account_id', () => {
    expect(() =>
      installmentPlanSchema.parse(basePlan({ billing_account: null, billing_account_id: null })),
    ).toThrow(ZodError);

    const result = installmentPlanSchema.safeParse(
      basePlan({ billing_account: null, billing_account_id: null }),
    );
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('billing_account_id'))).toBe(true);
    }
  });

  it('accepts a non-embedded plan with no account link', () => {
    const parsed = installmentPlanSchema.parse(
      basePlan({ embedded: false, billing_account: null, billing_account_id: null }),
    );
    expect(parsed.embedded).toBe(false);
  });
});
