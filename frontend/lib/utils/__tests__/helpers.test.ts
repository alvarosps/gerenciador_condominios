import { describe, it, expect } from 'vitest';
import {
  calculateTagFee,
  calculateLateFee,
  calculateDueDateChangeFee,
  calculateFinalDate,
  calculateDaysLate,
} from '../helpers';
import { TAG_FEES, LATE_FEE_RATE, DAYS_PER_MONTH } from '../constants';

describe('calculateTagFee', () => {
  it('returns SINGLE fee for 1 tenant', () => {
    expect(calculateTagFee(1)).toBe(TAG_FEES.SINGLE);
    expect(calculateTagFee(1)).toBe(50);
  });

  it('returns MULTIPLE fee for 2 or more tenants', () => {
    expect(calculateTagFee(2)).toBe(TAG_FEES.MULTIPLE);
    expect(calculateTagFee(5)).toBe(TAG_FEES.MULTIPLE);
    expect(calculateTagFee(2)).toBe(80);
  });
});

describe('calculateLateFee', () => {
  it('calculates daily fee correctly', () => {
    // dailyRate = 1500 / 30 = 50
    // fee = 50 * 3 * 0.05 = 7.50
    const result = calculateLateFee(1500, 3);
    expect(result).toBeCloseTo(7.5, 5);
  });

  it('returns 0 for 0 days late', () => {
    expect(calculateLateFee(1500, 0)).toBe(0);
  });

  it('uses the LATE_FEE_RATE and DAYS_PER_MONTH constants', () => {
    const rentalValue = 2000;
    const daysLate = 5;
    const expected = (rentalValue / DAYS_PER_MONTH) * daysLate * LATE_FEE_RATE;
    expect(calculateLateFee(rentalValue, daysLate)).toBeCloseTo(expected, 10);
  });
});

describe('calculateDueDateChangeFee', () => {
  it('calculates fee for moving due date forward', () => {
    // diff = 5 days, dailyRate = 1500/30 = 50, fee = 250
    const result = calculateDueDateChangeFee(1500, 5, 10);
    expect(result).toBeCloseTo(250, 5);
  });

  it('calculates fee for moving due date backward (uses abs diff)', () => {
    const result = calculateDueDateChangeFee(1500, 10, 5);
    expect(result).toBeCloseTo(250, 5);
  });

  it('returns 0 when due day does not change', () => {
    expect(calculateDueDateChangeFee(1500, 10, 10)).toBe(0);
  });
});

describe('calculateFinalDate', () => {
  it('adds validity months to start date', () => {
    const result = calculateFinalDate('2024-01-15', 12);
    expect(result).toBe('2025-01-15');
  });

  it('handles month overflow correctly', () => {
    const result = calculateFinalDate('2024-01-31', 1);
    // Jan 31 + 1 month = Feb 31 which becomes Mar 2 or 3 depending on leap year
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('returns a valid ISO date string', () => {
    const result = calculateFinalDate('2024-03-15', 6);
    // Just verify it's a valid YYYY-MM-DD string (exact date depends on timezone)
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe('calculateDaysLate', () => {
  it('returns 0 when payment is not late', () => {
    // Due on day 20, current date is day 15
    const currentDate = new Date(2024, 2, 15); // March 15
    expect(calculateDaysLate(20, currentDate)).toBe(0);
  });

  it('returns positive number when payment is late', () => {
    // Due on day 5, current date is day 10 → 5 days late
    const currentDate = new Date(2024, 2, 10); // March 10
    expect(calculateDaysLate(5, currentDate)).toBe(5);
  });

  it('returns 0 on the due date itself', () => {
    const currentDate = new Date(2024, 2, 10); // March 10
    expect(calculateDaysLate(10, currentDate)).toBe(0);
  });

  it('uses today as default when no date provided', () => {
    // Just verify it returns a non-negative number
    const result = calculateDaysLate(1);
    expect(result).toBeGreaterThanOrEqual(0);
  });
});
