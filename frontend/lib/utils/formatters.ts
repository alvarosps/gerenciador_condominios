/**
 * Format a number as Brazilian currency (R$)
 */
export function formatCurrency(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return 'R$ 0,00';
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(numValue)) return 'R$ 0,00';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(numValue);
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

// Alias for backward compatibility
export const formatCPFOrCNPJ = formatCpfCnpj;

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

// Alias for backward compatibility
export const formatBrazilianPhone = formatPhone;

/**
 * Format date to Brazilian format (DD/MM/YYYY)
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '';
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return '';
  return new Intl.DateTimeFormat('pt-BR').format(dateObj);
}

/**
 * Format date to ISO format (YYYY-MM-DD) for API
 */
export function formatDateISO(date: Date | null | undefined): string {
  if (!date) return '';
  if (isNaN(date.getTime())) return '';
  return date.toISOString().split('T')[0];
}
