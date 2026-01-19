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
};
