import type { Lease } from '@/lib/schemas/lease.schema';
import { mockApartments } from './apartments';
import { mockTenants } from './tenants';

/** Safe indexed access for mock arrays under noUncheckedIndexedAccess (no non-null assertions). */
function nth<T>(arr: readonly T[], index: number): T {
  const value = arr[index];
  if (value === undefined) {
    throw new Error(`Mock array missing index ${index}`);
  }
  return value;
}

export const mockLeases: Lease[] = [
  {
    id: 1,
    apartment_id: 1,
    apartment: nth(mockApartments, 0),
    responsible_tenant_id: 1,
    responsible_tenant: nth(mockTenants, 0),
    tenants: [nth(mockTenants, 0)],
    tenant_ids: [1],
    rental_value: 1500,
    resident_dependent: null,
    resident_dependent_id: null,
    start_date: '2024-01-15',
    final_date: '2025-01-14',
    next_month_date: '2024-02-15',
    validity_months: 12,
    tag_fee: 50.0,
    deposit_amount: 3000,
    cleaning_fee_paid: true,
    tag_deposit_paid: true,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    number_of_tenants: 1,
    pending_rental_value: null,
    pending_rental_value_date: null,
  },
  {
    id: 2,
    apartment_id: 2,
    apartment: nth(mockApartments, 1),
    responsible_tenant_id: 1,
    responsible_tenant: nth(mockTenants, 0),
    tenants: [nth(mockTenants, 0), nth(mockTenants, 1)],
    tenant_ids: [1, 2],
    rental_value: 1800,
    resident_dependent: null,
    resident_dependent_id: null,
    start_date: '2024-03-01',
    final_date: '2025-02-28',
    next_month_date: '2024-04-01',
    validity_months: 12,
    tag_fee: 80.0,
    deposit_amount: null,
    cleaning_fee_paid: false,
    tag_deposit_paid: false,
    contract_generated: true,
    contract_signed: false,
    interfone_configured: false,
    number_of_tenants: 2,
    pending_rental_value: null,
    pending_rental_value_date: null,
  },
  {
    id: 3,
    apartment_id: 3,
    apartment: nth(mockApartments, 2),
    responsible_tenant_id: 3,
    responsible_tenant: nth(mockTenants, 2),
    tenants: [nth(mockTenants, 2)],
    tenant_ids: [3],
    rental_value: 1200,
    resident_dependent: null,
    resident_dependent_id: null,
    start_date: '2024-06-01',
    final_date: '2025-05-31',
    next_month_date: '2024-07-01',
    validity_months: 12,
    tag_fee: 50.0,
    deposit_amount: 5000,
    cleaning_fee_paid: true,
    tag_deposit_paid: false,
    contract_generated: false,
    contract_signed: false,
    interfone_configured: false,
    number_of_tenants: 1,
    pending_rental_value: null,
    pending_rental_value_date: null,
  },
];

/**
 * Factory to create mock lease with custom overrides
 */
export function createMockLease(overrides: Partial<Lease> = {}): Lease {
  const apartment = nth(mockApartments, 0);
  const tenant = nth(mockTenants, 0);
  return {
    id: Math.floor(Math.random() * 1000) + 100,
    apartment_id: apartment.id ?? 1,
    apartment,
    responsible_tenant_id: tenant.id ?? 1,
    responsible_tenant: tenant,
    tenants: [tenant],
    tenant_ids: [tenant.id ?? 1],
    rental_value: apartment.rental_value,
    resident_dependent: null,
    resident_dependent_id: null,
    start_date: '2024-01-01',
    final_date: '2024-12-31',
    next_month_date: '2024-02-01',
    validity_months: 12,
    tag_fee: 50.0,
    deposit_amount: null,
    cleaning_fee_paid: false,
    tag_deposit_paid: false,
    contract_generated: false,
    contract_signed: false,
    interfone_configured: false,
    number_of_tenants: 1,
    pending_rental_value: null,
    pending_rental_value_date: null,
    ...overrides,
  };
}
