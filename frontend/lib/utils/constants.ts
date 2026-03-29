/**
 * Application-wide constants
 */

export const MARITAL_STATUS_OPTIONS = [
  { value: 'Solteiro(a)', label: 'Solteiro(a)' },
  { value: 'Casado(a)', label: 'Casado(a)' },
  { value: 'Divorciado(a)', label: 'Divorciado(a)' },
  { value: 'Viúvo(a)', label: 'Viúvo(a)' },
  { value: 'União Estável', label: 'União Estável' },
];

export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 10,
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
};

export const DATE_FORMAT = {
  DISPLAY: 'DD/MM/YYYY',
  API: 'YYYY-MM-DD',
};

export const TAG_FEES = {
  SINGLE: 50,
  MULTIPLE: 80,
};

export const LATE_FEE_RATE = 0.05; // 5% per day
export const DAYS_PER_MONTH = 30;

export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/',
  BUILDINGS: '/buildings',
  APARTMENTS: '/apartments',
  TENANTS: '/tenants',
  LEASES: '/leases',
  FURNITURE: '/furniture',
  CONTRACT_TEMPLATE: '/contract-template',
  SETTINGS: '/settings',
  FINANCIAL: '/financial',
  FINANCIAL_EXPENSES: '/financial/expenses',
  FINANCIAL_MONTHLY_PURCHASES: '/financial/monthly-purchases',
  FINANCIAL_INCOMES: '/financial/incomes',
  FINANCIAL_RENT_PAYMENTS: '/financial/rent-payments',
  FINANCIAL_PERSONS: '/financial/persons',
  FINANCIAL_PERSON_PAYMENTS: '/financial/person-payments',
  FINANCIAL_EMPLOYEES: '/financial/employees',
  FINANCIAL_CATEGORIES: '/financial/categories',
  FINANCIAL_SIMULATOR: '/financial/simulator',
  FINANCIAL_SETTINGS: '/financial/settings',
  FINANCIAL_DAILY: '/financial/daily',
  FINANCIAL_PERSON_INCOMES: '/financial/person-incomes',
};
