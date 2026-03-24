import { describe, it, expect } from 'vitest';
import {
  validateCPF,
  validateCNPJ,
  validateCpfCnpj,
  validateBrazilianPhone,
  validateEmail,
  validateCEP,
  formatCEP,
} from '../validators';

describe('validateCPF', () => {
  // Known valid CPFs (algorithmically correct)
  it('accepts a valid CPF', () => {
    expect(validateCPF('529.982.247-25')).toBe(true);
  });

  it('accepts a valid CPF without formatting', () => {
    expect(validateCPF('52998224725')).toBe(true);
  });

  it('rejects CPF with wrong length', () => {
    expect(validateCPF('1234567890')).toBe(false);   // 10 digits
    expect(validateCPF('123456789012')).toBe(false);  // 12 digits
  });

  it('rejects CPF with all identical digits', () => {
    expect(validateCPF('00000000000')).toBe(false);
    expect(validateCPF('11111111111')).toBe(false);
    expect(validateCPF('99999999999')).toBe(false);
  });

  it('rejects CPF with invalid check digits', () => {
    expect(validateCPF('52998224726')).toBe(false); // last digit changed
  });

  it('rejects empty string', () => {
    expect(validateCPF('')).toBe(false);
  });
});

describe('validateCNPJ', () => {
  // Known valid CNPJ
  it('accepts a valid CNPJ', () => {
    expect(validateCNPJ('11.222.333/0001-81')).toBe(true);
  });

  it('accepts a valid CNPJ without formatting', () => {
    expect(validateCNPJ('11222333000181')).toBe(true);
  });

  it('rejects CNPJ with wrong length', () => {
    expect(validateCNPJ('1234567890123')).toBe(false);   // 13 digits
    expect(validateCNPJ('123456789012345')).toBe(false); // 15 digits
  });

  it('rejects CNPJ with all identical digits', () => {
    expect(validateCNPJ('00000000000000')).toBe(false);
    expect(validateCNPJ('11111111111111')).toBe(false);
  });

  it('rejects CNPJ with invalid check digits', () => {
    expect(validateCNPJ('11222333000182')).toBe(false); // last digit changed
  });

  it('rejects empty string', () => {
    expect(validateCNPJ('')).toBe(false);
  });
});

describe('validateCpfCnpj', () => {
  it('validates 11-digit value as CPF', () => {
    expect(validateCpfCnpj('529.982.247-25')).toBe(true);
    expect(validateCpfCnpj('000.000.000-00')).toBe(false);
  });

  it('validates 14-digit value as CNPJ', () => {
    expect(validateCpfCnpj('11.222.333/0001-81')).toBe(true);
    expect(validateCpfCnpj('11.111.111/1111-11')).toBe(false);
  });

  it('returns false for other lengths', () => {
    expect(validateCpfCnpj('12345')).toBe(false);
    expect(validateCpfCnpj('')).toBe(false);
  });
});

describe('validateBrazilianPhone', () => {
  it('accepts valid 11-digit mobile number', () => {
    expect(validateBrazilianPhone('11987654321')).toBe(true);
    expect(validateBrazilianPhone('(11) 98765-4321')).toBe(true);
  });

  it('accepts valid 10-digit landline number', () => {
    expect(validateBrazilianPhone('1134567890')).toBe(true);
    expect(validateBrazilianPhone('(11) 3456-7890')).toBe(true);
  });

  it('rejects numbers with wrong digit count', () => {
    expect(validateBrazilianPhone('12345678')).toBe(false);   // 9 digits
    expect(validateBrazilianPhone('123456789012')).toBe(false); // 12 digits
  });

  it('rejects numbers starting with 0', () => {
    expect(validateBrazilianPhone('01987654321')).toBe(false);
  });

  it('rejects 11-digit mobile where third digit is not 9', () => {
    expect(validateBrazilianPhone('11887654321')).toBe(false); // third digit is 8
  });

  it('rejects empty string', () => {
    expect(validateBrazilianPhone('')).toBe(false);
  });
});

describe('validateEmail', () => {
  it('accepts valid email addresses', () => {
    expect(validateEmail('user@example.com')).toBe(true);
    expect(validateEmail('user.name+tag@domain.co.uk')).toBe(true);
  });

  it('rejects emails without @', () => {
    expect(validateEmail('userexample.com')).toBe(false);
  });

  it('rejects emails without domain', () => {
    expect(validateEmail('user@')).toBe(false);
  });

  it('rejects emails without TLD', () => {
    expect(validateEmail('user@domain')).toBe(false);
  });

  it('rejects emails with spaces', () => {
    expect(validateEmail('user @example.com')).toBe(false);
  });

  it('rejects empty string', () => {
    expect(validateEmail('')).toBe(false);
  });
});

describe('validateCEP', () => {
  it('accepts 8-digit CEP', () => {
    expect(validateCEP('01310100')).toBe(true);
    expect(validateCEP('01310-100')).toBe(true);
  });

  it('rejects CEP with wrong digit count', () => {
    expect(validateCEP('0131010')).toBe(false);  // 7 digits
    expect(validateCEP('013101000')).toBe(false); // 9 digits
  });

  it('rejects empty string', () => {
    expect(validateCEP('')).toBe(false);
  });
});

describe('formatCEP', () => {
  it('formats 8-digit string to XXXXX-XXX', () => {
    expect(formatCEP('01310100')).toBe('01310-100');
  });

  it('returns original string if not 8 digits', () => {
    expect(formatCEP('0131010')).toBe('0131010');
    expect(formatCEP('01310-100')).toBe('01310-100'); // already formatted strips to 8 and re-formats
  });
});
