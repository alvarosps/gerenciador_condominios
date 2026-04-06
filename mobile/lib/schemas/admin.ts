import { z } from "zod";

export const BuildingSchema = z.object({
  id: z.number(),
  street_number: z.string(),
  name: z.string(),
  address: z.string(),
});

export const ApartmentSchema = z.object({
  id: z.number(),
  number: z.string(),
  building: z.number(),
  rental_value: z.string(),
  rental_value_double: z.number(),
  is_rented: z.boolean(),
  max_tenants: z.number(),
});

export const LeaseSimpleSchema = z.object({
  id: z.number(),
  apartment: z.number(),
  responsible_tenant: z.object({
    id: z.number(),
    name: z.string(),
  }),
  start_date: z.string(),
  validity_months: z.number(),
  rental_value: z.string(),
  number_of_tenants: z.number(),
  contract_generated: z.boolean(),
});

export const FinancialSummarySchema = z.object({
  total_revenue: z.string(),
  total_apartments: z.number(),
  rented_apartments: z.number(),
  vacant_apartments: z.number(),
  occupancy_rate: z.number(),
});

export const LatePaymentItemSchema = z.object({
  tenant_name: z.string(),
  apartment_number: z.string(),
  building_name: z.string(),
  days_late: z.number(),
  amount_due: z.string(),
  late_fee: z.string(),
});

export const LeaseMetricsSchema = z.object({
  active_leases: z.number(),
  expired_leases: z.number(),
  expiring_soon: z.number(),
});

export const RentAdjustmentAlertSchema = z.object({
  lease_id: z.number(),
  tenant_name: z.string(),
  apartment_number: z.string(),
  months_since_adjustment: z.number(),
});

export const FinancialOverviewSchema = z.object({
  total_income: z.string(),
  total_expenses: z.string(),
  balance: z.string(),
  overdue_total: z.string(),
});

export const DailySummaryDataSchema = z.object({
  expected_income: z.string(),
  actual_income: z.string(),
  expected_expenses: z.string(),
  actual_expenses: z.string(),
});

export const MonthlyPurchaseGroupSchema = z.object({
  total: z.string(),
  count: z.number(),
  items: z.array(z.unknown()),
});

export const PaymentProofAdminSchema = z.object({
  id: z.number(),
  lease: z.number(),
  reference_month: z.string(),
  file: z.string(),
  status: z.enum(["pending", "approved", "rejected"]),
  created_at: z.string(),
  tenant_name: z.string().optional(),
  apartment_number: z.string().optional(),
});

export const TenantSearchResultSchema = z.object({
  id: z.number(),
  name: z.string(),
  cpf_cnpj: z.string(),
  phone: z.string(),
});

export type Building = z.infer<typeof BuildingSchema>;
export type Apartment = z.infer<typeof ApartmentSchema>;
export type LeaseSimple = z.infer<typeof LeaseSimpleSchema>;
export type FinancialSummary = z.infer<typeof FinancialSummarySchema>;
export type LatePaymentItem = z.infer<typeof LatePaymentItemSchema>;
export type LeaseMetrics = z.infer<typeof LeaseMetricsSchema>;
export type RentAdjustmentAlert = z.infer<typeof RentAdjustmentAlertSchema>;
export type FinancialOverview = z.infer<typeof FinancialOverviewSchema>;
export type DailySummaryData = z.infer<typeof DailySummaryDataSchema>;
export type MonthlyPurchaseGroup = z.infer<typeof MonthlyPurchaseGroupSchema>;
export type PaymentProofAdmin = z.infer<typeof PaymentProofAdminSchema>;
export type TenantSearchResult = z.infer<typeof TenantSearchResultSchema>;
