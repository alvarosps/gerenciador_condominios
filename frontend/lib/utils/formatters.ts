/**
 * Format a number as Brazilian currency (R$)
 * Rounds to 2 decimal places to avoid floating-point precision issues (e.g., 699.99 instead of 700)
 */
export function formatCurrency(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return 'R$ 0,00';
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return 'R$ 0,00';
  // Round to 2 decimal places to fix floating-point precision issues
  const roundedValue = Math.round(numValue * 100) / 100;
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(roundedValue);
}

/**
 * Format CPF (123.456.789-00)
 */
export function formatCPF(cpf: string): string {
  const clean = cpf.replace(/\D/g, '');
  if (clean.length !== 11) return cpf;
  return clean.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
}

/**
 * Format CNPJ (12.345.678/0001-90)
 */
export function formatCNPJ(cnpj: string): string {
  const clean = cnpj.replace(/\D/g, '');
  if (clean.length !== 14) return cnpj;
  return clean.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
}

/**
 * Format CPF or CNPJ automatically
 */
export function formatCpfCnpj(value: string): string {
  const clean = value.replace(/\D/g, '');
  if (clean.length === 11) return formatCPF(clean);
  if (clean.length === 14) return formatCNPJ(clean);
  return value;
}

/**
 * Format Brazilian phone number (11) 98765-4321
 */
export function formatPhone(phone: string): string {
  const clean = phone.replace(/\D/g, '');
  if (clean.length === 11) {
    return clean.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
  }
  if (clean.length === 10) {
    return clean.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
  }
  return phone;
}

/**
 * Parse a date string into a Date.
 *
 * Date-only ISO strings (YYYY-MM-DD) are parsed as LOCAL calendar dates rather
 * than UTC midnight, avoiding the off-by-one day shift that `new Date('YYYY-MM-DD')`
 * causes in negative-offset timezones (e.g. Brazil UTC−3). Strings carrying a time
 * component fall back to the native parser.
 */
function parseDateString(value: string): Date {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (dateOnly) {
    const [, year, month, day] = dateOnly;
    return new Date(Number(year), Number(month) - 1, Number(day));
  }
  return new Date(value);
}

/**
 * Format date to Brazilian format (DD/MM/YYYY)
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '';
  const dateObj = typeof date === 'string' ? parseDateString(date) : date;
  if (isNaN(dateObj.getTime())) return '';
  return new Intl.DateTimeFormat('pt-BR').format(dateObj);
}

/**
 * Format month/year in Portuguese (e.g., "Março/2026")
 */
export function formatMonthYear(year: number, month: number): string {
  const date = new Date(year, month - 1, 1);
  const formatted = new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' }).format(
    date
  );
  return formatted.charAt(0).toUpperCase() + formatted.slice(1);
}

/**
 * Format date to ISO format (YYYY-MM-DD) for API
 */
export function formatDateISO(date: Date | null | undefined): string {
  if (!date) return '';
  if (isNaN(date.getTime())) return '';
  return date.toISOString().split('T')[0] ?? '';
}

export const MONTH_ABBR = [
  'Jan',
  'Fev',
  'Mar',
  'Abr',
  'Mai',
  'Jun',
  'Jul',
  'Ago',
  'Set',
  'Out',
  'Nov',
  'Dez',
] as const;

export const MONTH_NAMES = [
  'Janeiro',
  'Fevereiro',
  'Março',
  'Abril',
  'Maio',
  'Junho',
  'Julho',
  'Agosto',
  'Setembro',
  'Outubro',
  'Novembro',
  'Dezembro',
] as const;

/**
 * Calculate a default expense date for a given target year/month.
 * Uses today's day number, clamped to the last day of the target month.
 */
export function getDefaultExpenseDate(year: number, month: number): string {
  const today = new Date();
  const day = today.getDate();
  const lastDay = new Date(year, month, 0).getDate();
  const targetDay = Math.min(day, lastDay);
  return `${String(year)}-${String(month).padStart(2, '0')}-${String(targetDay).padStart(2, '0')}`;
}

/**
 * Get today's date as a LOCAL YYYY-MM-DD string.
 *
 * Unlike `new Date().toISOString().split('T')[0]`, this does not shift to
 * UTC first, so it never rolls back a day in negative-offset timezones
 * (e.g. Brazil UTC−3 in the early hours).
 */
export function getTodayLocalISO(): string {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${String(year)}-${month}-${day}`;
}

/**
 * Compare a YYYY-MM-DD date string against today (local), lexicographically.
 * Returns true when `dateStr` is strictly before today's local date.
 *
 * Lexicographic comparison is safe and equivalent to calendar comparison
 * for zero-padded ISO date-only strings, and avoids any Date/timezone
 * parsing pitfalls entirely.
 */
export function isDateStringBeforeToday(dateStr: string): boolean {
  return dateStr < getTodayLocalISO();
}

/**
 * Compare a YYYY-MM-DD date string against today (local), lexicographically.
 * Returns true when `dateStr` is strictly after today's local date.
 */
export function isDateStringAfterToday(dateStr: string): boolean {
  return dateStr > getTodayLocalISO();
}

/**
 * Add `n` months to a YYYY-MM-DD date string, using pure calendar arithmetic on the
 * year/month/day components — never `Date`/`setMonth`/`toISOString`.
 *
 * The day is clamped to the last day of the target month (e.g. 31/01 + 1 month -> 28/02 or
 * 29/02 in a leap year; 30/03 + 1 month -> 30/04), mirroring the backend's day-clamping
 * (`RentScheduleService.clamp_due_day` / `finances/services/installment_plan_service.py::_schedule_due_dates`).
 *
 * `n` may be negative to go backward. Timezone-independent: `Date`/`setMonth` shift a UTC
 * instant, which drifts a day in negative-offset timezones (e.g. Brazil UTC-3); this function
 * only ever does integer arithmetic on the string's own year/month/day.
 */
export function addMonthsClamped(dateStr: string, n: number): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateStr);
  if (!match) {
    throw new Error(`addMonthsClamped: invalid date string "${dateStr}"`);
  }
  const [, yearStr, monthStr, dayStr] = match;
  const totalMonths = Number(yearStr) * 12 + (Number(monthStr) - 1) + n;
  const targetYear = Math.floor(totalMonths / 12);
  const targetMonth = totalMonths - targetYear * 12; // 0-indexed
  const lastDayOfTargetMonth = new Date(targetYear, targetMonth + 1, 0).getDate();
  const targetDay = Math.min(Number(dayStr), lastDayOfTargetMonth);
  return `${String(targetYear)}-${String(targetMonth + 1).padStart(2, '0')}-${String(targetDay).padStart(2, '0')}`;
}
