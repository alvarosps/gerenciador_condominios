import { DAYS_PER_MONTH, LATE_FEE_RATE, TAG_FEES } from './constants';

/**
 * Calculate tag fee based on number of tenants
 */
export function calculateTagFee(numberOfTenants: number): number {
  return numberOfTenants === 1 ? TAG_FEES.SINGLE : TAG_FEES.MULTIPLE;
}

/**
 * Calculate late fee based on rental value and days late
 */
export function calculateLateFee(rentalValue: number, daysLate: number): number {
  const dailyRate = rentalValue / DAYS_PER_MONTH;
  return dailyRate * daysLate * LATE_FEE_RATE;
}

/**
 * Calculate due date change fee
 */
export function calculateDueDateChangeFee(
  rentalValue: number,
  currentDueDay: number,
  newDueDay: number
): number {
  const diffDays = Math.abs(newDueDay - currentDueDay);
  const dailyRate = rentalValue / DAYS_PER_MONTH;
  return dailyRate * diffDays;
}

/**
 * Calculate final date based on start date and validity months
 */
export function calculateFinalDate(startDate: string, validityMonths: number): string {
  const date = new Date(startDate);
  date.setMonth(date.getMonth() + validityMonths);
  return date.toISOString().split('T')[0];
}

/**
 * Calculate days late from due date
 */
export function calculateDaysLate(dueDay: number, currentDate: Date = new Date()): number {
  const dueDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), dueDay);
  const diffTime = currentDate.getTime() - dueDate.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays > 0 ? diffDays : 0;
}
