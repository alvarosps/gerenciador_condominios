/**
 * Expense type field visibility configuration.
 * Centralizes which fields are required/optional/visible per expense type.
 */

export const EXPENSE_TYPES = [
  'card_purchase',
  'bank_loan',
  'personal_loan',
  'water_bill',
  'electricity_bill',
  'property_tax',
  'fixed_expense',
  'one_time_expense',
] as const;

export type ExpenseType = (typeof EXPENSE_TYPES)[number];

export const PERSON_REQUIRED_TYPES: readonly ExpenseType[] = [
  'card_purchase',
  'bank_loan',
  'personal_loan',
];

export const PERSON_OPTIONAL_TYPES: readonly ExpenseType[] = [
  'one_time_expense',
  'fixed_expense',
];

export const BUILDING_REQUIRED_TYPES: readonly ExpenseType[] = [
  'water_bill',
  'electricity_bill',
  'property_tax',
];

export const BUILDING_OPTIONAL_TYPES: readonly ExpenseType[] = [
  'fixed_expense',
  'one_time_expense',
];

export const OFFSET_TYPES: readonly ExpenseType[] = [
  'card_purchase',
  'bank_loan',
  'personal_loan',
];

export const INSTALLMENT_TYPES: readonly ExpenseType[] = [
  'card_purchase',
  'bank_loan',
  'personal_loan',
];

export const DEBT_INSTALLMENT_TYPES: readonly ExpenseType[] = [
  'water_bill',
  'electricity_bill',
  'property_tax',
];

export function isPersonFieldVisible(type: string): boolean {
  return (
    PERSON_REQUIRED_TYPES.includes(type as ExpenseType) ||
    PERSON_OPTIONAL_TYPES.includes(type as ExpenseType)
  );
}

export function isBuildingFieldVisible(type: string): boolean {
  return (
    BUILDING_REQUIRED_TYPES.includes(type as ExpenseType) ||
    BUILDING_OPTIONAL_TYPES.includes(type as ExpenseType)
  );
}

export function isInstallmentFieldVisible(type: string): boolean {
  return INSTALLMENT_TYPES.includes(type as ExpenseType);
}

export function isOffsetFieldVisible(type: string): boolean {
  return OFFSET_TYPES.includes(type as ExpenseType);
}

export function isDebtInstallmentFieldVisible(type: string): boolean {
  return DEBT_INSTALLMENT_TYPES.includes(type as ExpenseType);
}

export function isValidExpenseType(type: string): type is ExpenseType {
  return EXPENSE_TYPES.includes(type as ExpenseType);
}
