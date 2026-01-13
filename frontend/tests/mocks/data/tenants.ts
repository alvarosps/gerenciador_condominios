import type { Tenant, Dependent } from '@/lib/schemas/tenant.schema';

export const mockDependents: Dependent[] = [
  {
    id: 1,
    name: 'Ana Silva',
    phone: '(11) 91234-5678',
  },
  {
    id: 2,
    name: 'Pedro Silva',
    phone: '(11) 91234-5679',
  },
];

export const mockTenants: Tenant[] = [
  {
    id: 1,
    name: 'Carlos Eduardo da Silva',
    cpf_cnpj: '12345678909',
    is_company: false,
    rg: '123456789',
    phone: '(11) 98765-4321',
    phone_alternate: '(11) 91234-5678',
    email: 'carlos.silva@email.com',
    marital_status: 'Casado',
    profession: 'Engenheiro',
    deposit_amount: 3000,
    cleaning_fee_paid: true,
    tag_deposit_paid: true,
    rent_due_day: 10,
    furnitures: [],
    dependents: mockDependents,
  },
  {
    id: 2,
    name: 'Maria Oliveira Santos',
    cpf_cnpj: '98765432100',
    is_company: false,
    rg: '987654321',
    phone: '(11) 98765-4322',
    phone_alternate: null,
    email: 'maria.santos@email.com',
    marital_status: 'Solteira',
    profession: 'Advogada',
    deposit_amount: null,
    cleaning_fee_paid: false,
    tag_deposit_paid: false,
    rent_due_day: 5,
    furnitures: [],
    dependents: [],
  },
  {
    id: 3,
    name: 'Tech Solutions LTDA',
    cpf_cnpj: '12345678000190',
    is_company: true,
    rg: null,
    phone: '(11) 3456-7890',
    phone_alternate: '(11) 3456-7891',
    email: 'contato@techsolutions.com.br',
    marital_status: 'N/A',
    profession: 'Empresa de Tecnologia',
    deposit_amount: 5000,
    cleaning_fee_paid: true,
    tag_deposit_paid: true,
    rent_due_day: 15,
    furnitures: [],
    dependents: [],
  },
];

/**
 * Factory to create mock tenant with custom overrides
 */
export function createMockTenant(overrides: Partial<Tenant> = {}): Tenant {
  return {
    id: Math.floor(Math.random() * 1000) + 100,
    name: `Inquilino Teste ${Math.floor(Math.random() * 100)}`,
    cpf_cnpj: '12345678909',
    is_company: false,
    rg: '123456789',
    phone: '(11) 98765-4321',
    phone_alternate: null,
    email: 'teste@email.com',
    marital_status: 'Solteiro(a)',
    profession: 'Profissão Teste',
    deposit_amount: null,
    cleaning_fee_paid: false,
    tag_deposit_paid: false,
    rent_due_day: 10,
    furnitures: [],
    dependents: [],
    ...overrides,
  };
}
