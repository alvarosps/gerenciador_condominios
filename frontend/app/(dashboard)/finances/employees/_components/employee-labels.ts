import type { EmployeePaymentType } from '@/lib/schemas/finances/employee.schema';

/** Single source of truth for payment-type labels (PT), reused by columns and the form. */
export const PAYMENT_TYPE_LABELS: Record<EmployeePaymentType, string> = {
  fixed: 'Fixo',
  variable: 'Variável',
  mixed: 'Misto',
};
