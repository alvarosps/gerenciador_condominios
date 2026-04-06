import { describe, it, expect } from 'vitest';
import {
  formatCurrency,
  formatCPF,
  formatCNPJ,
  formatCpfCnpj,
  formatPhone,
  formatDate,
  formatMonthYear,
  formatDateISO,
} from '../formatters';

describe('formatCurrency', () => {
  it('formats positive numbers as BRL currency', () => {
    const result = formatCurrency(1500);
    expect(result).toContain('1.500');
    expect(result).toContain('R$');
  });

  it('formats zero', () => {
    expect(formatCurrency(0)).toContain('0,00');
    expect(formatCurrency(0)).toContain('R$');
  });

  it('returns R$ 0,00 for null', () => {
    const result = formatCurrency(null);
    expect(result).toContain('R$');
    expect(result).toContain('0,00');
  });

  it('returns R$ 0,00 for undefined', () => {
    const result = formatCurrency(undefined);
    expect(result).toContain('R$');
    expect(result).toContain('0,00');
  });

  it('parses string numbers', () => {
    const result = formatCurrency('1500.50');
    expect(result).toContain('1.500');
    expect(result).toContain('50');
  });

  it('returns R$ 0,00 for NaN strings', () => {
    const result = formatCurrency('abc');
    expect(result).toContain('R$');
    expect(result).toContain('0,00');
  });

  it('rounds floating-point precision issues', () => {
    // 699.995 should round to 700.00, not 699.99
    const result = formatCurrency(699.995);
    expect(result).toContain('700');
  });

  it('formats negative values', () => {
    const result = formatCurrency(-100);
    expect(result).toContain('100');
  });
});

describe('formatCPF', () => {
  it('formats a clean 11-digit string', () => {
    expect(formatCPF('12345678900')).toBe('123.456.789-00');
  });

  it('formats a pre-formatted CPF (strips and re-formats)', () => {
    expect(formatCPF('123.456.789-00')).toBe('123.456.789-00');
  });

  it('returns original string if not 11 digits', () => {
    expect(formatCPF('1234567')).toBe('1234567');
  });
});

describe('formatCNPJ', () => {
  it('formats a clean 14-digit string', () => {
    expect(formatCNPJ('12345678000190')).toBe('12.345.678/0001-90');
  });

  it('formats a pre-formatted CNPJ (strips and re-formats)', () => {
    expect(formatCNPJ('12.345.678/0001-90')).toBe('12.345.678/0001-90');
  });

  it('returns original string if not 14 digits', () => {
    expect(formatCNPJ('1234')).toBe('1234');
  });
});

describe('formatCpfCnpj', () => {
  it('formats 11-digit value as CPF', () => {
    expect(formatCpfCnpj('12345678900')).toBe('123.456.789-00');
  });

  it('formats 14-digit value as CNPJ', () => {
    expect(formatCpfCnpj('12345678000190')).toBe('12.345.678/0001-90');
  });

  it('returns original for other lengths', () => {
    expect(formatCpfCnpj('12345')).toBe('12345');
  });

});

describe('formatPhone', () => {
  it('formats 11-digit mobile number', () => {
    expect(formatPhone('11987654321')).toBe('(11) 98765-4321');
  });

  it('formats 10-digit landline number', () => {
    expect(formatPhone('1134567890')).toBe('(11) 3456-7890');
  });

  it('formats from formatted input', () => {
    expect(formatPhone('(11) 98765-4321')).toBe('(11) 98765-4321');
  });

  it('returns original for other lengths', () => {
    expect(formatPhone('1234')).toBe('1234');
  });

});

describe('formatDate', () => {
  it('formats ISO date string to DD/MM/YYYY', () => {
    // Use a UTC noon to avoid timezone shifts
    const result = formatDate('2024-03-15T12:00:00.000Z');
    expect(result).toMatch(/15\/03\/2024/);
  });

  it('formats Date object', () => {
    const date = new Date(2024, 2, 15); // March 15, 2024 (month is 0-indexed)
    const result = formatDate(date);
    expect(result).toContain('15');
    expect(result).toContain('2024');
  });

  it('returns empty string for null', () => {
    expect(formatDate(null)).toBe('');
  });

  it('returns empty string for undefined', () => {
    expect(formatDate(undefined)).toBe('');
  });

  it('returns empty string for invalid date string', () => {
    expect(formatDate('not-a-date')).toBe('');
  });
});

describe('formatMonthYear', () => {
  it('formats month and year in Portuguese with capitalized first letter', () => {
    const result = formatMonthYear(2026, 3);
    // Should contain "março" or "Março" and "2026"
    expect(result).toMatch(/[Mm]arço/);
    expect(result).toContain('2026');
  });

  it('first letter is uppercase', () => {
    const result = formatMonthYear(2026, 1);
    expect(result[0]).toBe(result[0]?.toUpperCase());
  });
});

describe('formatDateISO', () => {
  it('formats a Date to YYYY-MM-DD', () => {
    const date = new Date('2024-03-15T12:00:00.000Z');
    expect(formatDateISO(date)).toBe('2024-03-15');
  });

  it('returns empty string for null', () => {
    expect(formatDateISO(null)).toBe('');
  });

  it('returns empty string for undefined', () => {
    expect(formatDateISO(undefined)).toBe('');
  });

  it('returns empty string for invalid Date', () => {
    expect(formatDateISO(new Date('invalid'))).toBe('');
  });
});
