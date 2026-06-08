export const queryKeys = {
  apartments: {
    all: ['apartments'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.apartments.all, filters] as const,
    detail: (id: number) => [...queryKeys.apartments.all, id] as const,
  },
  buildings: {
    all: ['buildings'] as const,
    list: () => [...queryKeys.buildings.all] as const,
    detail: (id: number) => [...queryKeys.buildings.all, id] as const,
  },
  tenants: {
    all: ['tenants'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.tenants.all, filters] as const,
    detail: (id: number) => [...queryKeys.tenants.all, id] as const,
  },
  leases: {
    all: ['leases'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.leases.all, filters] as const,
    detail: (id: number) => [...queryKeys.leases.all, id] as const,
  },
  expenses: {
    all: ['expenses'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.expenses.all, filters] as const,
    detail: (id: number) => [...queryKeys.expenses.all, id] as const,
  },
  expenseInstallments: {
    all: ['expense-installments'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.expenseInstallments.all, filters] as const,
  },
  expenseCategories: {
    all: ['expense-categories'] as const,
    list: () => [...queryKeys.expenseCategories.all] as const,
    detail: (id: number) => [...queryKeys.expenseCategories.all, id] as const,
  },
  expenseMonthSkips: {
    all: ['expense-month-skips'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.expenseMonthSkips.all, filters] as const,
  },
  persons: {
    all: ['persons'] as const,
    list: () => [...queryKeys.persons.all] as const,
    detail: (id: number) => [...queryKeys.persons.all, id] as const,
  },
  creditCards: {
    all: ['credit-cards'] as const,
    list: () => [...queryKeys.creditCards.all] as const,
    detail: (id: number) => [...queryKeys.creditCards.all, id] as const,
  },
  incomes: {
    all: ['incomes'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.incomes.all, filters] as const,
    detail: (id: number) => [...queryKeys.incomes.all, id] as const,
  },
  rentPayments: {
    all: ['rent-payments'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.rentPayments.all, filters] as const,
    detail: (id: number) => [...queryKeys.rentPayments.all, id] as const,
  },
  employeePayments: {
    all: ['employee-payments'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.employeePayments.all, filters] as const,
    detail: (id: number) => [...queryKeys.employeePayments.all, id] as const,
  },
  personIncomes: {
    all: ['person-incomes'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.personIncomes.all, filters] as const,
  },
  personPayments: {
    all: ['person-payments'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.personPayments.all, filters] as const,
  },
  personPaymentSchedules: {
    all: ['person-payment-schedules'] as const,
    list: (filters?: Record<string, unknown>) =>
      [...queryKeys.personPaymentSchedules.all, filters] as const,
    personMonthTotal: (personId: number | undefined, referenceMonth: string | undefined) =>
      [
        ...queryKeys.personPaymentSchedules.all,
        'person_month_total',
        personId,
        referenceMonth,
      ] as const,
  },
  dailyControl: {
    all: ['daily-control'] as const,
    breakdown: (year: number, month: number) =>
      [...queryKeys.dailyControl.all, 'breakdown', year, month] as const,
    summary: (year: number, month: number) =>
      [...queryKeys.dailyControl.all, 'summary', year, month] as const,
  },
  cashFlow: {
    all: ['cash-flow'] as const,
    monthly: (year: number, month: number) =>
      [...queryKeys.cashFlow.all, 'monthly', year, month] as const,
    projection: (params: Record<string, string | number>) =>
      [...queryKeys.cashFlow.all, 'projection', params] as const,
    personSummary: (personId: number, year: number, month: number) =>
      [...queryKeys.cashFlow.all, 'person_summary', personId, year, month] as const,
  },
  financialDashboard: {
    all: ['financial-dashboard'] as const,
    overview: () => [...queryKeys.financialDashboard.all, 'overview'] as const,
    debtByPerson: () => [...queryKeys.financialDashboard.all, 'debt_by_person'] as const,
    debtByType: () => [...queryKeys.financialDashboard.all, 'debt_by_type'] as const,
    upcomingInstallments: (days?: number) =>
      [...queryKeys.financialDashboard.all, 'upcoming_installments', days] as const,
    overdueInstallments: () =>
      [...queryKeys.financialDashboard.all, 'overdue_installments'] as const,
    categoryBreakdown: (year: number, month: number) =>
      [...queryKeys.financialDashboard.all, 'category_breakdown', year, month] as const,
    dashboardSummary: (year: number, month: number) =>
      [...queryKeys.financialDashboard.all, 'dashboard_summary', year, month] as const,
    expenseDetail: (type: string, id: number | null, year: number, month: number) =>
      [...queryKeys.financialDashboard.all, 'expense_detail', type, id, year, month] as const,
  },
  dashboard: {
    all: ['dashboard'] as const,
    financialSummary: () => [...queryKeys.dashboard.all, 'financial_summary'] as const,
    leaseMetrics: () => [...queryKeys.dashboard.all, 'lease_metrics'] as const,
    buildingStatistics: () => [...queryKeys.dashboard.all, 'building_statistics'] as const,
    latePaymentSummary: () => [...queryKeys.dashboard.all, 'late_payment_summary'] as const,
    tenantStatistics: () => [...queryKeys.dashboard.all, 'tenant_statistics'] as const,
  },
  rentCalendar: {
    all: ['rent-calendar'] as const,
    month: (year: number, month: number, buildingId?: number) =>
      [...queryKeys.rentCalendar.all, 'month', year, month, buildingId ?? null] as const,
  },
  finances: {
    all: ['finances'] as const,
    billingAccounts: {
      all: ['finances', 'billing-accounts'] as const,
      list: (filters?: Record<string, unknown>) =>
        [...queryKeys.finances.billingAccounts.all, filters ?? null] as const,
      detail: (id: number) => [...queryKeys.finances.billingAccounts.all, id] as const,
    },
    bills: {
      all: ['finances', 'bills'] as const,
      list: (filters?: Record<string, unknown>) =>
        [...queryKeys.finances.bills.all, filters ?? null] as const,
      detail: (id: number) => [...queryKeys.finances.bills.all, id] as const,
    },
    payments: {
      all: ['finances', 'payments'] as const,
      list: (filters?: Record<string, unknown>) =>
        [...queryKeys.finances.payments.all, filters ?? null] as const,
      detail: (id: number) => [...queryKeys.finances.payments.all, id] as const,
    },
    financeCategories: {
      all: ['finances', 'finance-categories'] as const,
      list: () => [...queryKeys.finances.financeCategories.all, 'list'] as const,
    },
    billSkips: {
      all: ['finances', 'bill-skips'] as const,
      list: (filters?: Record<string, unknown>) =>
        [...queryKeys.finances.billSkips.all, filters ?? null] as const,
    },
    combinedCalendar: {
      all: ['finances', 'combined-calendar'] as const,
      month: (year: number, month: number, buildingId?: number) =>
        [
          ...queryKeys.finances.combinedCalendar.all,
          'month',
          year,
          month,
          buildingId ?? null,
        ] as const,
    },
    overdueBills: {
      all: ['finances', 'overdue-bills'] as const,
      list: (buildingId?: number) =>
        [...queryKeys.finances.overdueBills.all, buildingId ?? null] as const,
    },
    installmentPlans: {
      all: ['finances', 'installment-plans'] as const,
      list: (filters?: Record<string, unknown>) =>
        [...queryKeys.finances.installmentPlans.all, filters ?? null] as const,
      detail: (id: number) => [...queryKeys.finances.installmentPlans.all, id] as const,
    },
    installments: {
      all: ['finances', 'installments'] as const,
      list: (filters?: Record<string, unknown>) =>
        [...queryKeys.finances.installments.all, filters ?? null] as const,
      detail: (id: number) => [...queryKeys.finances.installments.all, id] as const,
    },
    employees: {
      all: ['finances', 'employees'] as const,
      list: (filters?: Record<string, unknown>) =>
        [...queryKeys.finances.employees.all, filters ?? null] as const,
      detail: (id: number) => [...queryKeys.finances.employees.all, id] as const,
    },
    reserves: {
      all: ['finances', 'reserves'] as const,
      list: (filters?: Record<string, unknown>) =>
        [...queryKeys.finances.reserves.all, filters ?? null] as const,
      detail: (id: number) => [...queryKeys.finances.reserves.all, id] as const,
    },
    reserveMovements: {
      all: ['finances', 'reserve-movements'] as const,
      list: (filters?: Record<string, unknown>) =>
        [...queryKeys.finances.reserveMovements.all, filters ?? null] as const,
      detail: (id: number) => [...queryKeys.finances.reserveMovements.all, id] as const,
    },
    incomeEntries: {
      all: ['finances', 'income-entries'] as const,
      list: (filters?: Record<string, unknown>) =>
        [...queryKeys.finances.incomeEntries.all, filters ?? null] as const,
      detail: (id: number) => [...queryKeys.finances.incomeEntries.all, id] as const,
    },
    condoMonthCloses: {
      all: ['finances', 'condo-month-closes'] as const,
      list: (filters?: Record<string, unknown>) =>
        [...queryKeys.finances.condoMonthCloses.all, filters ?? null] as const,
      detail: (id: number) => [...queryKeys.finances.condoMonthCloses.all, id] as const,
    },
    overview: {
      all: ['finances', 'overview'] as const,
      month: (year: number, month: number, buildingId?: number | null) =>
        [...queryKeys.finances.overview.all, 'month', year, month, buildingId ?? null] as const,
    },
    monthlyBalance: {
      all: ['finances', 'monthly-balance'] as const,
      year: (year: number) => [...queryKeys.finances.monthlyBalance.all, year] as const,
    },
    byCategory: {
      all: ['finances', 'by-category'] as const,
      month: (year: number, month: number, buildingId?: number | null) =>
        [...queryKeys.finances.byCategory.all, 'month', year, month, buildingId ?? null] as const,
    },
    projection: {
      all: ['finances', 'projection'] as const,
      list: (months: number) => [...queryKeys.finances.projection.all, months] as const,
    },
    simulation: {
      all: ['finances', 'simulation'] as const,
    },
  },
  rentAdjustments: {
    all: ['rent-adjustments'] as const,
    byLease: (leaseId: number | null) => [...queryKeys.rentAdjustments.all, leaseId] as const,
  },
  rentAdjustmentAlerts: {
    all: ['rent-adjustment-alerts'] as const,
  },
  monthAdvance: {
    all: ['month-advance'] as const,
    status: (year: number, month: number) =>
      [...queryKeys.monthAdvance.all, 'status', year, month] as const,
    snapshots: (year?: number) => [...queryKeys.monthAdvance.all, 'snapshots', year] as const,
    snapshotDetail: (year: number, month: number) =>
      [...queryKeys.monthAdvance.all, 'snapshot-detail', year, month] as const,
    preview: (year: number, month: number) =>
      [...queryKeys.monthAdvance.all, 'preview', year, month] as const,
  },
  monthlyPurchases: {
    all: ['monthly-purchases'] as const,
    byMonth: (year: number, month: number) =>
      [...queryKeys.monthlyPurchases.all, year, month] as const,
  },
  adminUsers: {
    all: ['admin-users'] as const,
    list: () => [...queryKeys.adminUsers.all] as const,
  },
  landlord: {
    all: ['landlord'] as const,
    current: () => [...queryKeys.landlord.all, 'current'] as const,
  },
  contractTemplate: {
    all: ['contract-template'] as const,
  },
  templateBackups: {
    all: ['template-backups'] as const,
  },
  contractRules: {
    all: ['contract-rules'] as const,
    list: (activeOnly: boolean) => [...queryKeys.contractRules.all, { activeOnly }] as const,
    detail: (id: number) => [...queryKeys.contractRules.all, id] as const,
  },
  furniture: {
    all: ['furniture'] as const,
    list: () => [...queryKeys.furniture.all] as const,
    detail: (id: number) => [...queryKeys.furniture.all, id] as const,
  },
  financialSettings: {
    all: ['financial-settings'] as const,
    current: () => [...queryKeys.financialSettings.all, 'current'] as const,
  },
  currentUser: {
    all: ['current-user'] as const,
  },
} as const;
