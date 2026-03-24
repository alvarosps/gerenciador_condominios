import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';

export interface FinancialOverview {
  current_month_balance: number;
  current_month_income: number;
  current_month_expenses: number;
  total_debt: number;
  total_monthly_obligations: number;
  total_monthly_income: number;
  months_until_break_even: number | null;
}

export interface DebtByPerson {
  person_id: number;
  person_name: string;
  card_debt: number;
  loan_debt: number;
  total_debt: number;
  monthly_card: number;
  monthly_loan: number;
  cards_count: number;
}

export interface DebtByType {
  expense_type: string;
  total: number;
}

export interface UpcomingInstallment {
  id: number;
  expense_description: string;
  expense_type: string;
  person_name: string | null;
  credit_card_nickname: string | null;
  installment_number: number;
  total_installments: number;
  amount: number;
  due_date: string;
  days_until_due?: number;
  days_overdue?: number;
}

export interface CategoryBreakdown {
  category_id: number | null;
  category_name: string;
  color: string;
  total: number;
  percentage: number;
  count: number;
}

export interface ApartmentInfo {
  apartment_number: string;
  building_name: string;
  rental_value?: number;
}

export interface OwnerIncome {
  person_name: string;
  total: number;
  apartments: string[];
}

export interface ExpenseDetail {
  description: string;
  amount: number;
  card_name?: string | null;
  installment?: string;
  building_name?: string | null;
}

export interface PersonExpenseSummary {
  person_id: number;
  person_name: string;
  card_total: number;
  card_details: ExpenseDetail[];
  loan_total: number;
  loan_details: ExpenseDetail[];
  fixed_total: number;
  fixed_details: ExpenseDetail[];
  one_time_total: number;
  one_time_details: ExpenseDetail[];
  offset_total: number;
  offset_details: ExpenseDetail[];
  stipend_total: number;
  stipend_details: ExpenseDetail[];
  total: number;
  total_paid: number;
  pending: number;
  is_payable: boolean;
}

export interface ExtraIncome {
  description: string;
  amount: number;
  is_recurring: boolean;
  person_name: string | null;
}

export interface UtilityBuildingEntry {
  building_name: string;
  bills: ExpenseDetail[];
  debt_installments: ExpenseDetail[];
  bill_total: number;
  debt_total: number;
  total: number;
  notes: string[];
}

export interface UtilityExpense {
  total: number;
  by_building: UtilityBuildingEntry[];
}

export interface SimpleExpenseGroup {
  total: number;
  details: ExpenseDetail[];
}

export interface OverdueItem {
  type: 'person' | 'iptu';
  person_id?: number;
  person_name?: string;
  description?: string;
  building_name?: string | null;
  reference_year: number;
  reference_month: number;
  amount: number;
  net_amount?: number;
  total_paid?: number;
  installment?: string;
  due_date?: string;
}

export interface ExpenseDetailItem {
  expense_id: number;
  installment_id?: number | null;
  description: string;
  card_name?: string | null;
  installment_number?: number | null;
  total_installments?: number | null;
  category_id?: number | null;
  category_name?: string | null;
  category_color?: string | null;
  subcategory_id?: number | null;
  subcategory_name?: string | null;
  notes?: string | null;
  amount: number;
  due_date?: string | null;
}

export interface ExpenseDetailResponse {
  detail_type: string;
  person_id?: number;
  person_name?: string;
  total?: number;
  total_paid?: number;
  pending?: number;
  is_payable?: boolean;
  card_total?: number;
  card_details?: ExpenseDetailItem[];
  loan_total?: number;
  loan_details?: ExpenseDetailItem[];
  fixed_total?: number;
  fixed_details?: ExpenseDetailItem[];
  one_time_total?: number;
  one_time_details?: ExpenseDetailItem[];
  offset_total?: number;
  offset_details?: ExpenseDetailItem[];
  stipend_total?: number;
  stipend_details?: ExpenseDetailItem[];
  by_building?: UtilityBuildingEntry[];
  details?: ExpenseDetailItem[];
  label?: string;
}

export interface DashboardSummary {
  year: number;
  month: number;
  overdue_items: OverdueItem[];
  income_summary: {
    total_monthly_income: number;
    all_apartments: ApartmentInfo[];
    owner_incomes: OwnerIncome[];
    owner_total: number;
    vacant_kitnets: ApartmentInfo[];
    vacant_by_building: { building_name: string; apartments: string[] }[];
    vacant_count: number;
    vacant_lost_rent: number;
    condominium_income: number;
    condominium_kitnet_count: number;
    extra_incomes: ExtraIncome[];
    extra_income_total: number;
  };
  expense_summary: {
    by_person: PersonExpenseSummary[];
    water: UtilityExpense;
    electricity: UtilityExpense;
    iptu: UtilityExpense;
    internet: SimpleExpenseGroup;
    celular: SimpleExpenseGroup;
    sitio: SimpleExpenseGroup;
    outros_fixed: SimpleExpenseGroup;
    employee: SimpleExpenseGroup;
    total: number;
  };
  overdue_total: number;
  monthly_expenses: number;
  current_month_income: number;
  current_month_expenses: number;
  current_month_balance: number;
}

const STALE_TIME = 1000 * 60 * 5;
const REFETCH_INTERVAL = 1000 * 60 * 5;

export function useFinancialOverview() {
  return useQuery({
    queryKey: ['financial-dashboard', 'overview'],
    queryFn: async () => {
      const { data } = await apiClient.get<FinancialOverview>('/financial-dashboard/overview/');
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useDebtByPerson() {
  return useQuery({
    queryKey: ['financial-dashboard', 'debt_by_person'],
    queryFn: async () => {
      const { data } = await apiClient.get<DebtByPerson[]>('/financial-dashboard/debt_by_person/');
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useDebtByType() {
  return useQuery({
    queryKey: ['financial-dashboard', 'debt_by_type'],
    queryFn: async () => {
      const { data } = await apiClient.get<DebtByType[]>('/financial-dashboard/debt_by_type/');
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useUpcomingInstallments(days?: number) {
  return useQuery({
    queryKey: ['financial-dashboard', 'upcoming_installments', days],
    queryFn: async () => {
      const { data } = await apiClient.get<Record<string, unknown>[]>(
        '/financial-dashboard/upcoming_installments/',
        { params: days ? { days } : undefined },
      );
      return data.map((item) => ({
        ...item,
        amount: Number(item.amount),
      })) as UpcomingInstallment[];
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useOverdueInstallments() {
  return useQuery({
    queryKey: ['financial-dashboard', 'overdue_installments'],
    queryFn: async () => {
      const { data } = await apiClient.get<Record<string, unknown>[]>(
        '/financial-dashboard/overdue_installments/',
      );
      return data.map((item) => ({
        ...item,
        amount: Number(item.amount),
      })) as UpcomingInstallment[];
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useCategoryBreakdown(year: number, month: number) {
  return useQuery({
    queryKey: ['financial-dashboard', 'category_breakdown', year, month],
    queryFn: async () => {
      const { data } = await apiClient.get<CategoryBreakdown[]>(
        '/financial-dashboard/category_breakdown/',
        { params: { year, month } },
      );
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useDashboardSummary(year: number, month: number) {
  return useQuery({
    queryKey: ['financial-dashboard', 'dashboard_summary', year, month],
    queryFn: async () => {
      const { data } = await apiClient.get<DashboardSummary>(
        '/financial-dashboard/dashboard_summary/',
        { params: { year, month } },
      );
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useExpenseDetail(type: string, id: number | null, year: number, month: number) {
  return useQuery({
    queryKey: ['financial-dashboard', 'expense_detail', type, id, year, month],
    queryFn: async () => {
      const params: Record<string, string | number> = { type, year, month };
      if (id !== null) params.id = id;
      const { data } = await apiClient.get<ExpenseDetailResponse>(
        '/financial-dashboard/expense_detail/',
        { params },
      );
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
    enabled: Boolean(type),
  });
}
