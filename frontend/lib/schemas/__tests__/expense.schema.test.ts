import { describe, it, expect } from 'vitest';
import { expenseReadSchema, expenseSchema } from '@/lib/schemas/expense.schema';

// A read payload from the API: write-only person_id/credit_card_id/building_id are absent
// (the serializer exposes them only nested). validateExpenseRules requires the *_id fields,
// so applying it on read threw a ZodError that emptied the whole list (P4.3 regression).
const cardPurchaseRead = {
  id: 1,
  description: 'Compra no cartão',
  expense_type: 'card_purchase',
  total_amount: '500.00',
  expense_date: '2026-01-10',
  is_installment: false,
  installments: [],
};

describe('expenseReadSchema', () => {
  it('parses a card_purchase read payload without the write-only _id fields', () => {
    expect(() => expenseReadSchema.parse(cardPurchaseRead)).not.toThrow();
  });

  it('keeps the nested fields optional so a read never depends on _id presence', () => {
    const fixedExpenseRead = {
      ...cardPurchaseRead,
      expense_type: 'fixed_expense',
      description: 'Internet',
    };
    expect(() => expenseReadSchema.parse(fixedExpenseRead)).not.toThrow();
  });
});

describe('expenseSchema (form)', () => {
  it('still requires person_id/credit_card_id for a card_purchase form', () => {
    const result = expenseSchema.safeParse(cardPurchaseRead);
    expect(result.success).toBe(false);
  });

  it('does not require a person for fixed_expense (PERSON_REQUIRED_TYPES fix)', () => {
    const result = expenseSchema.safeParse({
      ...cardPurchaseRead,
      expense_type: 'fixed_expense',
      description: 'Internet',
    });
    expect(result.success).toBe(true);
  });
});
