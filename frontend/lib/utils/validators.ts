/**
 * Validate Brazilian CPF
 */
export function validateCPF(cpf: string): boolean {
  const cleanCPF = cpf.replace(/\D/g, '');
  if (cleanCPF.length !== 11) return false;

  // Check if all digits are the same
  if (/^(\d)\1{10}$/.test(cleanCPF)) return false;

  // Validate first check digit
  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(cleanCPF.charAt(i)) * (10 - i);
  }
  let checkDigit = 11 - (sum % 11);
  if (checkDigit >= 10) checkDigit = 0;
  if (checkDigit !== parseInt(cleanCPF.charAt(9))) return false;

  // Validate second check digit
  sum = 0;
  for (let i = 0; i < 10; i++) {
    sum += parseInt(cleanCPF.charAt(i)) * (11 - i);
  }
  checkDigit = 11 - (sum % 11);
  if (checkDigit >= 10) checkDigit = 0;
  if (checkDigit !== parseInt(cleanCPF.charAt(10))) return false;

  return true;
}

/**
 * Validate Brazilian CNPJ
 */
export function validateCNPJ(cnpj: string): boolean {
  const cleanCNPJ = cnpj.replace(/\D/g, '');
  if (cleanCNPJ.length !== 14) return false;

  // Check if all digits are the same
  if (/^(\d)\1{13}$/.test(cleanCNPJ)) return false;

  // Validate first check digit
  let length = cleanCNPJ.length - 2;
  let numbers = cleanCNPJ.substring(0, length);
  const digits = cleanCNPJ.substring(length);
  let sum = 0;
  let pos = length - 7;

  for (let i = length; i >= 1; i--) {
    sum += parseInt(numbers.charAt(length - i)) * pos--;
    if (pos < 2) pos = 9;
  }

  let result = sum % 11 < 2 ? 0 : 11 - (sum % 11);
  if (result !== parseInt(digits.charAt(0))) return false;

  // Validate second check digit
  length = length + 1;
  numbers = cleanCNPJ.substring(0, length);
  sum = 0;
  pos = length - 7;

  for (let i = length; i >= 1; i--) {
    sum += parseInt(numbers.charAt(length - i)) * pos--;
    if (pos < 2) pos = 9;
  }

  result = sum % 11 < 2 ? 0 : 11 - (sum % 11);
  if (result !== parseInt(digits.charAt(1))) return false;

  return true;
}

/**
 * Validate CPF or CNPJ automatically
 */
export function validateCpfCnpj(value: string): boolean {
  const clean = value.replace(/\D/g, '');
  if (clean.length === 11) return validateCPF(clean);
  if (clean.length === 14) return validateCNPJ(clean);
  return false;
}

/**
 * Validate Brazilian phone number
 * Accepts formats: (XX) XXXXX-XXXX or (XX) XXXX-XXXX
 *
 * @param phone - Phone string with or without formatting
 * @returns true if valid, false otherwise
 */
export function validateBrazilianPhone(phone: string): boolean {
  const digits = phone.replace(/\D/g, '');

  // Must have 10 (landline) or 11 (mobile) digits
  if (digits.length !== 10 && digits.length !== 11) return false;

  // First digit must be 1-9 (area code can't start with 0)
  if (digits[0] === '0') return false;

  // For mobile (11 digits), the third digit must be 9
  if (digits.length === 11 && digits[2] !== '9') return false;

  return true;
}

/**
 * Validate email format
 * @param email - Email string
 * @returns true if valid, false otherwise
 */
export function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validate Brazilian CEP (postal code)
 * CEP format: XXXXX-XXX (8 digits)
 *
 * @param cep - CEP string with or without formatting
 * @returns true if valid, false otherwise
 */
export function validateCEP(cep: string): boolean {
  const digits = cep.replace(/\D/g, '');
  return digits.length === 8;
}

/**
 * Format CEP for display
 * @param cep - CEP string with only digits
 * @returns Formatted CEP (XXXXX-XXX)
 */
export function formatCEP(cep: string): string {
  const digits = cep.replace(/\D/g, '');
  if (digits.length !== 8) return cep;

  return digits.replace(/(\d{5})(\d{3})/, '$1-$2');
}
