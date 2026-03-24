/**
 * MSW Request Handlers for API mocking
 *
 * These handlers intercept HTTP requests during tests and return mock data.
 * They simulate the Django REST Framework API endpoints.
 */

import { http, HttpResponse, delay } from 'msw';
import {
  mockBuildings,
  mockFurniture,
  mockApartments,
  mockTenants,
  mockLeases,
  mockPersons,
  mockExpenses,
  mockPersonPayments,
  createMockBuilding,
  createMockFurniture,
  createMockApartment,
  createMockTenant,
  createMockLease,
  createMockPerson,
  createMockExpense,
  createMockPersonPayment,
} from './data';

const API_BASE = 'http://localhost:8000/api';

// Mutable copies for CRUD operations during tests
let buildings = [...mockBuildings];
let furniture = [...mockFurniture];
let apartments = [...mockApartments];
let tenants = [...mockTenants];
let leases = [...mockLeases];
let persons = [...mockPersons];
let expenses = [...mockExpenses];
let personPayments = [...mockPersonPayments];

// Helper to reset data between tests
export function resetMockData() {
  buildings = [...mockBuildings];
  furniture = [...mockFurniture];
  apartments = [...mockApartments];
  tenants = [...mockTenants];
  leases = [...mockLeases];
  persons = [...mockPersons];
  expenses = [...mockExpenses];
  personPayments = [...mockPersonPayments];
}

/**
 * Building handlers
 */
const buildingHandlers = [
  // List buildings
  http.get(`${API_BASE}/buildings/`, async () => {
    await delay(50);
    return HttpResponse.json(buildings);
  }),

  // Get single building
  http.get(`${API_BASE}/buildings/:id/`, async ({ params }) => {
    await delay(50);
    const id = Number(params.id);
    const building = buildings.find((b) => b.id === id);
    if (!building) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(building);
  }),

  // Create building
  http.post(`${API_BASE}/buildings/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as Omit<(typeof buildings)[0], 'id'>;
    const newBuilding = createMockBuilding({ ...data, id: buildings.length + 1 });
    buildings.push(newBuilding);
    return HttpResponse.json(newBuilding, { status: 201 });
  }),

  // Update building
  http.put(`${API_BASE}/buildings/:id/`, async ({ params, request }) => {
    await delay(100);
    const id = Number(params.id);
    const data = (await request.json()) as (typeof buildings)[0];
    const index = buildings.findIndex((b) => b.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    buildings[index] = { ...buildings[index], ...data };
    return HttpResponse.json(buildings[index]);
  }),

  // Delete building
  http.delete(`${API_BASE}/buildings/:id/`, async ({ params }) => {
    await delay(100);
    const id = Number(params.id);
    const index = buildings.findIndex((b) => b.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    buildings.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),
];

/**
 * Furniture handlers
 */
const furnitureHandlers = [
  // List furniture
  http.get(`${API_BASE}/furnitures/`, async () => {
    await delay(50);
    return HttpResponse.json(furniture);
  }),

  // Get single furniture
  http.get(`${API_BASE}/furnitures/:id/`, async ({ params }) => {
    await delay(50);
    const id = Number(params.id);
    const item = furniture.find((f) => f.id === id);
    if (!item) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(item);
  }),

  // Create furniture
  http.post(`${API_BASE}/furnitures/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as Omit<(typeof furniture)[0], 'id'>;
    const newFurniture = createMockFurniture({ ...data, id: furniture.length + 1 });
    furniture.push(newFurniture);
    return HttpResponse.json(newFurniture, { status: 201 });
  }),

  // Update furniture
  http.put(`${API_BASE}/furnitures/:id/`, async ({ params, request }) => {
    await delay(100);
    const id = Number(params.id);
    const data = (await request.json()) as (typeof furniture)[0];
    const index = furniture.findIndex((f) => f.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    furniture[index] = { ...furniture[index], ...data };
    return HttpResponse.json(furniture[index]);
  }),

  // Delete furniture
  http.delete(`${API_BASE}/furnitures/:id/`, async ({ params }) => {
    await delay(100);
    const id = Number(params.id);
    const index = furniture.findIndex((f) => f.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    furniture.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),
];

/**
 * Apartment handlers
 */
const apartmentHandlers = [
  // List apartments
  http.get(`${API_BASE}/apartments/`, async () => {
    await delay(50);
    return HttpResponse.json(apartments);
  }),

  // Get single apartment
  http.get(`${API_BASE}/apartments/:id/`, async ({ params }) => {
    await delay(50);
    const id = Number(params.id);
    const apartment = apartments.find((a) => a.id === id);
    if (!apartment) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(apartment);
  }),

  // Create apartment
  http.post(`${API_BASE}/apartments/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as Omit<(typeof apartments)[0], 'id'>;
    const newApartment = createMockApartment({ ...data, id: apartments.length + 1 });
    apartments.push(newApartment);
    return HttpResponse.json(newApartment, { status: 201 });
  }),

  // Update apartment
  http.put(`${API_BASE}/apartments/:id/`, async ({ params, request }) => {
    await delay(100);
    const id = Number(params.id);
    const data = (await request.json()) as (typeof apartments)[0];
    const index = apartments.findIndex((a) => a.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    apartments[index] = { ...apartments[index], ...data };
    return HttpResponse.json(apartments[index]);
  }),

  // Delete apartment
  http.delete(`${API_BASE}/apartments/:id/`, async ({ params }) => {
    await delay(100);
    const id = Number(params.id);
    const index = apartments.findIndex((a) => a.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    apartments.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),
];

/**
 * Tenant handlers
 */
const tenantHandlers = [
  // List tenants
  http.get(`${API_BASE}/tenants/`, async () => {
    await delay(50);
    return HttpResponse.json(tenants);
  }),

  // Get single tenant
  http.get(`${API_BASE}/tenants/:id/`, async ({ params }) => {
    await delay(50);
    const id = Number(params.id);
    const tenant = tenants.find((t) => t.id === id);
    if (!tenant) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(tenant);
  }),

  // Create tenant
  http.post(`${API_BASE}/tenants/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as Omit<(typeof tenants)[0], 'id'>;
    const newTenant = createMockTenant({ ...data, id: tenants.length + 1 });
    tenants.push(newTenant);
    return HttpResponse.json(newTenant, { status: 201 });
  }),

  // Update tenant
  http.put(`${API_BASE}/tenants/:id/`, async ({ params, request }) => {
    await delay(100);
    const id = Number(params.id);
    const data = (await request.json()) as (typeof tenants)[0];
    const index = tenants.findIndex((t) => t.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    tenants[index] = { ...tenants[index], ...data };
    return HttpResponse.json(tenants[index]);
  }),

  // Delete tenant
  http.delete(`${API_BASE}/tenants/:id/`, async ({ params }) => {
    await delay(100);
    const id = Number(params.id);
    const index = tenants.findIndex((t) => t.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    tenants.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),
];

/**
 * Lease handlers
 */
const leaseHandlers = [
  // List leases
  http.get(`${API_BASE}/leases/`, async () => {
    await delay(50);
    return HttpResponse.json(leases);
  }),

  // Get single lease
  http.get(`${API_BASE}/leases/:id/`, async ({ params }) => {
    await delay(50);
    const id = Number(params.id);
    const lease = leases.find((l) => l.id === id);
    if (!lease) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(lease);
  }),

  // Create lease
  http.post(`${API_BASE}/leases/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as Omit<(typeof leases)[0], 'id'>;
    const newLease = createMockLease({ ...data, id: leases.length + 1 });
    leases.push(newLease);
    return HttpResponse.json(newLease, { status: 201 });
  }),

  // Update lease
  http.put(`${API_BASE}/leases/:id/`, async ({ params, request }) => {
    await delay(100);
    const id = Number(params.id);
    const data = (await request.json()) as (typeof leases)[0];
    const index = leases.findIndex((l) => l.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    leases[index] = { ...leases[index], ...data };
    return HttpResponse.json(leases[index]);
  }),

  // Delete lease
  http.delete(`${API_BASE}/leases/:id/`, async ({ params }) => {
    await delay(100);
    const id = Number(params.id);
    const index = leases.findIndex((l) => l.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    leases.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  // Generate contract
  http.post(`${API_BASE}/leases/:id/generate_contract/`, async ({ params }) => {
    await delay(200);
    const id = Number(params.id);
    const index = leases.findIndex((l) => l.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    const lease = leases[index];
    if (!lease) {
      return new HttpResponse(null, { status: 404 });
    }
    lease.contract_generated = true;
    lease.pdf_path = `contracts/mock/contract_${id}.pdf`;
    return HttpResponse.json({
      message: 'Contract generated successfully',
      pdf_path: lease.pdf_path,
    });
  }),

  // Calculate late fee
  http.get(`${API_BASE}/leases/:id/calculate_late_fee/`, async ({ params }) => {
    await delay(50);
    const id = Number(params.id);
    const lease = leases.find((l) => l.id === id);
    if (!lease) {
      return new HttpResponse(null, { status: 404 });
    }
    // Mock late fee calculation
    const dailyRate = (lease.apartment?.rental_value ?? 0) / 30;
    const lateFeePerDay = dailyRate * 0.05;
    return HttpResponse.json({
      daily_rate: dailyRate,
      late_fee_per_day: lateFeePerDay,
      days_late: 5,
      total_late_fee: lateFeePerDay * 5,
    });
  }),

  // Change due date
  http.post(`${API_BASE}/leases/:id/change_due_date/`, async ({ params, request }) => {
    await delay(100);
    const id = Number(params.id);
    const data = (await request.json()) as { new_due_day: number };
    const index = leases.findIndex((l) => l.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    const existingLease = leases[index];
    if (!existingLease) {
      return new HttpResponse(null, { status: 404 });
    }
    const oldDueDay = existingLease.responsible_tenant?.due_day ?? 0;
    if (existingLease.responsible_tenant) {
      existingLease.responsible_tenant.due_day = data.new_due_day;
    }
    return HttpResponse.json({
      message: 'Due date changed successfully',
      old_due_day: oldDueDay,
      new_due_day: data.new_due_day,
      adjustment_fee: Math.abs(data.new_due_day - oldDueDay) * 50,
    });
  }),
];

/**
 * Auth handlers
 */
const authHandlers = [
  // Login
  http.post(`${API_BASE}/auth/login/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as { email: string; password: string };
    if (data.email === 'test@example.com' && data.password === 'password123') {
      return HttpResponse.json({
        access: 'mock-access-token-12345',
        refresh: 'mock-refresh-token-67890',
        user: {
          id: 1,
          email: 'test@example.com',
          first_name: 'Test',
          last_name: 'User',
        },
      });
    }
    return HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 });
  }),

  // Register
  http.post(`${API_BASE}/auth/register/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as {
      email: string;
      password: string;
      password2: string;
      first_name: string;
      last_name: string;
    };
    if (data.password !== data.password2) {
      return HttpResponse.json({ detail: 'Passwords do not match' }, { status: 400 });
    }
    return HttpResponse.json({
      access: 'mock-access-token-12345',
      refresh: 'mock-refresh-token-67890',
      user: {
        id: 2,
        email: data.email,
        first_name: data.first_name,
        last_name: data.last_name,
      },
    }, { status: 201 });
  }),

  // Refresh token
  http.post(`${API_BASE}/auth/token/refresh/`, async ({ request }) => {
    await delay(50);
    const data = (await request.json()) as { refresh: string };
    if (data.refresh === 'mock-refresh-token-67890') {
      return HttpResponse.json({
        access: 'mock-new-access-token-54321',
      });
    }
    return HttpResponse.json({ detail: 'Token is invalid or expired' }, { status: 401 });
  }),

  // Logout
  http.post(`${API_BASE}/auth/logout/`, async () => {
    await delay(50);
    return new HttpResponse(null, { status: 204 });
  }),

  // Get current user
  http.get(`${API_BASE}/auth/user/`, async () => {
    await delay(50);
    return HttpResponse.json({
      id: 1,
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
    });
  }),
];

/**
 * Dashboard handlers
 */
const dashboardHandlers = [
  // Financial summary
  http.get(`${API_BASE}/dashboard/financial_summary/`, async () => {
    await delay(50);
    const totalRevenue = leases.reduce((sum, l) => sum + (l.apartment?.rental_value ?? 0), 0);
    return HttpResponse.json({
      total_revenue: totalRevenue,
      avg_rental_value: leases.length > 0 ? totalRevenue / leases.length : 0,
      total_cleaning_fees: leases.reduce((sum, l) => sum + (l.apartment?.cleaning_fee ?? 0), 0),
      total_late_fees: 250.0,
      occupancy_rate: apartments.length > 0 ? (leases.length / apartments.length) * 100 : 0,
    });
  }),

  // Lease metrics
  http.get(`${API_BASE}/dashboard/lease_metrics/`, async () => {
    await delay(50);
    return HttpResponse.json({
      total_leases: leases.length,
      active_leases: leases.filter((l) => l.contract_generated).length,
      expired_leases: 0,
      expiring_soon: 1,
      avg_validity_months: 12,
    });
  }),

  // Building statistics
  http.get(`${API_BASE}/dashboard/building_statistics/`, async () => {
    await delay(50);
    return HttpResponse.json(
      buildings.map((b, index) => ({
        building_id: b.id,
        building_name: b.name,
        total_apartments: 10,
        rented_apartments: 8,
        occupancy_rate: 80.0,
        total_revenue: 8000.0 + index * 1000,
      }))
    );
  }),

  // Late payment summary
  http.get(`${API_BASE}/dashboard/late_payment_summary/`, async () => {
    await delay(50);
    return HttpResponse.json([
      {
        lease_id: 1,
        tenant_name: 'João Silva',
        building: 'Building A',
        apartment_number: 101,
        days_late: 5,
        late_fee: 75.0,
      },
    ]);
  }),

  // Tenant statistics
  http.get(`${API_BASE}/dashboard/tenant_statistics/`, async () => {
    await delay(50);
    return HttpResponse.json({
      total_tenants: tenants.length,
      tenants_with_dependents: 3,
      avg_dependents: 1.5,
      tenants_with_furniture: 2,
      company_tenants: 1,
      person_tenants: Math.max(0, tenants.length - 1),
    });
  }),
];

/**
 * Person handlers
 */
const personHandlers = [
  http.get(`${API_BASE}/persons/`, async () => {
    await delay(50);
    return HttpResponse.json(persons);
  }),

  http.get(`${API_BASE}/persons/:id/`, async ({ params }) => {
    await delay(50);
    const id = Number(params.id);
    const person = persons.find((p) => p.id === id);
    if (!person) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(person);
  }),

  http.post(`${API_BASE}/persons/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as Record<string, unknown>;
    const newPerson = createMockPerson({ ...data, id: persons.length + 1 } as Partial<(typeof persons)[0]>);
    persons.push(newPerson);
    return HttpResponse.json(newPerson, { status: 201 });
  }),

  http.put(`${API_BASE}/persons/:id/`, async ({ params, request }) => {
    await delay(100);
    const id = Number(params.id);
    const data = (await request.json()) as (typeof persons)[0];
    const index = persons.findIndex((p) => p.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    persons[index] = { ...persons[index], ...data };
    return HttpResponse.json(persons[index]);
  }),

  http.delete(`${API_BASE}/persons/:id/`, async ({ params }) => {
    await delay(100);
    const id = Number(params.id);
    const index = persons.findIndex((p) => p.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    persons.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),
];

/**
 * Expense handlers
 */
const expenseHandlers = [
  http.get(`${API_BASE}/expenses/`, async () => {
    await delay(50);
    return HttpResponse.json(expenses);
  }),

  http.get(`${API_BASE}/expenses/:id/`, async ({ params }) => {
    await delay(50);
    const id = Number(params.id);
    const expense = expenses.find((e) => e.id === id);
    if (!expense) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(expense);
  }),

  http.post(`${API_BASE}/expenses/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as Record<string, unknown>;
    const newExpense = createMockExpense({ ...data, id: expenses.length + 1 } as Partial<(typeof expenses)[0]>);
    expenses.push(newExpense);
    return HttpResponse.json(newExpense, { status: 201 });
  }),

  http.post(`${API_BASE}/expenses/:id/mark_paid/`, async ({ params }) => {
    await delay(100);
    const id = Number(params.id);
    const index = expenses.findIndex((e) => e.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    const existing = expenses[index];
    if (!existing) {
      return new HttpResponse(null, { status: 404 });
    }
    expenses[index] = { ...existing, is_paid: true, paid_date: '2026-03-22' };
    return HttpResponse.json(expenses[index]);
  }),

  http.post(`${API_BASE}/expenses/:id/generate_installments/`, async ({ params }) => {
    await delay(100);
    const id = Number(params.id);
    const expense = expenses.find((e) => e.id === id);
    if (!expense) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({
      message: 'Parcelas geradas com sucesso',
      installments_created: expense.total_installments ?? 1,
    });
  }),
];

/**
 * Expense installment handlers
 */
const expenseInstallmentHandlers = [
  http.get(`${API_BASE}/expense-installments/`, async () => {
    await delay(50);
    const allInstallments = expenses.flatMap((e) => e.installments);
    return HttpResponse.json(allInstallments);
  }),

  http.post(`${API_BASE}/expense-installments/:id/mark_paid/`, async ({ params }) => {
    await delay(100);
    const id = Number(params.id);
    return HttpResponse.json({
      id,
      is_paid: true,
      paid_date: '2026-03-22',
    });
  }),

  http.post(`${API_BASE}/expense-installments/bulk_mark_paid/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as { ids: number[] };
    return HttpResponse.json({
      message: `${data.ids.length} parcelas marcadas como pagas`,
      updated_count: data.ids.length,
    });
  }),
];

/**
 * Financial dashboard handlers
 */
const financialDashboardHandlers = [
  http.get(`${API_BASE}/financial-dashboard/overview/`, async () => {
    await delay(50);
    return HttpResponse.json({
      current_month_balance: 6800.0,
      current_month_income: 12000.0,
      current_month_expenses: 5200.0,
      total_debt: 2300.0,
      total_monthly_obligations: 3200.0,
      total_monthly_income: 12000.0,
      months_until_break_even: null,
    });
  }),

  http.get(`${API_BASE}/financial-dashboard/debt_by_person/`, async () => {
    await delay(50);
    return HttpResponse.json([
      { person_id: 1, person_name: 'Rodrigo Souza', card_debt: 1000.0, loan_debt: 500.0, total_debt: 1500.0, monthly_card: 200.0, monthly_loan: 100.0, cards_count: 2 },
      { person_id: 3, person_name: 'Alvaro Souza', card_debt: 800.0, loan_debt: 0, total_debt: 800.0, monthly_card: 150.0, monthly_loan: 0, cards_count: 3 },
    ]);
  }),

  http.get(`${API_BASE}/financial-dashboard/debt_by_type/`, async () => {
    await delay(50);
    return HttpResponse.json({
      card_purchases: 2500.0,
      bank_loans: 700.0,
      personal_loans: 500.0,
      water_debt: 0,
      electricity_debt: 0,
      property_tax_debt: 0,
      total: 3700.0,
    });
  }),

  http.get(`${API_BASE}/financial-dashboard/upcoming_installments/`, async () => {
    await delay(50);
    return HttpResponse.json([
      {
        id: 2,
        expense_description: 'Supermercado Extra',
        expense_type: 'card_purchase',
        person_name: 'Alvaro Souza',
        credit_card_nickname: 'Trigg',
        installment_number: 2,
        total_installments: 3,
        amount: '150.00',
        due_date: '2026-04-10',
        days_until_due: 19,
      },
    ]);
  }),

  http.get(`${API_BASE}/financial-dashboard/overdue_installments/`, async () => {
    await delay(50);
    return HttpResponse.json([]);
  }),

  http.get(`${API_BASE}/financial-dashboard/category_breakdown/`, async () => {
    await delay(50);
    return HttpResponse.json([
      { category_id: 1, category_name: 'Pessoal', color: '#3b82f6', total: 2500.0, percentage: 48.1, count: 5 },
      { category_id: 2, category_name: 'Kitnets', color: '#10b981', total: 1700.0, percentage: 32.7, count: 3 },
      { category_id: 3, category_name: 'Carros', color: '#f59e0b', total: 1000.0, percentage: 19.2, count: 2 },
    ]);
  }),
];

/**
 * Cash flow handlers
 */
const cashFlowHandlers = [
  http.get(`${API_BASE}/cash-flow/monthly/`, async () => {
    await delay(50);
    return HttpResponse.json({
      year: 2026,
      month: 3,
      income: {
        rent_income: 10000.0,
        rent_details: [
          { apartment_id: 1, apartment_number: '101', building_name: '836', tenant_name: 'João Silva', rental_value: 1300.0, is_paid: true, payment_date: '2026-03-05' },
        ],
        extra_income: 2000.0,
        extra_income_details: [],
        total: 12000.0,
      },
      expenses: {
        owner_repayments: 0,
        person_stipends: 1100.0,
        card_installments: 1500.0,
        loan_installments: 500.0,
        utility_bills: 300.0,
        debt_installments: 0,
        property_tax: 200.0,
        employee_salary: 800.0,
        fixed_expenses: 500.0,
        one_time_expenses: 300.0,
        total: 5200.0,
      },
      balance: 6800.0,
    });
  }),

  http.get(`${API_BASE}/cash-flow/projection/`, async () => {
    await delay(50);
    return HttpResponse.json([
      { year: 2026, month: 3, income_total: 12000.0, expenses_total: 5200.0, balance: 6800.0, cumulative_balance: 16800.0, is_projected: false },
      { year: 2026, month: 4, income_total: 12000.0, expenses_total: 5100.0, balance: 6900.0, cumulative_balance: 23700.0, is_projected: true },
      { year: 2026, month: 5, income_total: 12000.0, expenses_total: 5000.0, balance: 7000.0, cumulative_balance: 30700.0, is_projected: true },
    ]);
  }),

  http.get(`${API_BASE}/cash-flow/person_summary/`, async () => {
    await delay(50);
    return HttpResponse.json({
      person_id: 1,
      person_name: 'Rodrigo Souza',
      receives: 1100.0,
      receives_details: [{ description: 'Estipêndio fixo', amount: 1100.0, source: 'fixed_stipend' }],
      card_total: 300.0,
      card_details: [{ description: 'Supermercado', card_name: 'Trigg', installment: '2/3', amount: 150.0, due_date: '2026-03-10' }],
      loan_total: 0,
      loan_details: [],
      offset_total: 100.0,
      offset_details: [{ description: 'Presente sogra', installment: '1/2', amount: 100.0, due_date: '2026-03-15' }],
      fixed_total: 0,
      fixed_details: [],
      net_amount: 900.0,
      total_paid: 500.0,
      payment_details: [{ amount: 500.0, payment_date: '2026-03-01', notes: 'Pagamento parcial' }],
      pending_balance: 400.0,
    });
  }),

  http.post(`${API_BASE}/cash-flow/simulate/`, async () => {
    await delay(100);
    const baseMonth = {
      year: 2026,
      month: 4,
      income_total: 12000.0,
      expenses_total: 8000.0,
      balance: 4000.0,
      cumulative_balance: 4000.0,
      is_projected: true,
    };
    const simMonth = {
      year: 2026,
      month: 4,
      income_total: 12000.0,
      expenses_total: 5000.0,
      balance: 7000.0,
      cumulative_balance: 7000.0,
      is_projected: true,
    };
    return HttpResponse.json({
      base: [baseMonth],
      simulated: [simMonth],
      comparison: {
        month_by_month: [
          {
            year: 2026,
            month: 4,
            base_balance: 4000.0,
            simulated_balance: 7000.0,
            delta: 3000.0,
            base_cumulative: 4000.0,
            simulated_cumulative: 7000.0,
          },
        ],
        total_impact_12m: 3000.0,
        break_even_month: '2026-04',
      },
    });
  }),
];

/**
 * Income handlers
 */
const incomeHandlers = [
  http.get(`${API_BASE}/incomes/`, async () => {
    await delay(50);
    return HttpResponse.json([]);
  }),
  http.post(`${API_BASE}/incomes/:id/mark_received/`, async () => {
    await delay(100);
    return HttpResponse.json({ is_received: true, received_date: '2026-03-22' });
  }),
];

/**
 * Employee payment handlers
 */
const employeePaymentHandlers = [
  http.get(`${API_BASE}/employee-payments/`, async () => {
    await delay(50);
    return HttpResponse.json([]);
  }),
  http.post(`${API_BASE}/employee-payments/:id/mark_paid/`, async () => {
    await delay(100);
    return HttpResponse.json({ is_paid: true, payment_date: '2026-03-22' });
  }),
];

/**
 * Person payment handlers
 */
const personPaymentHandlers = [
  http.get(`${API_BASE}/person-payments/`, async () => {
    await delay(50);
    return HttpResponse.json(personPayments);
  }),

  http.post(`${API_BASE}/person-payments/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as Record<string, unknown>;
    const newPayment = createMockPersonPayment({ ...data, id: personPayments.length + 1 } as Partial<(typeof personPayments)[0]>);
    personPayments.push(newPayment);
    return HttpResponse.json(newPayment, { status: 201 });
  }),

  http.put(`${API_BASE}/person-payments/:id/`, async ({ params, request }) => {
    await delay(100);
    const id = Number(params.id);
    const data = (await request.json()) as (typeof personPayments)[0];
    const index = personPayments.findIndex((p) => p.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    personPayments[index] = { ...personPayments[index], ...data };
    return HttpResponse.json(personPayments[index]);
  }),

  http.delete(`${API_BASE}/person-payments/:id/`, async ({ params }) => {
    await delay(100);
    const id = Number(params.id);
    const index = personPayments.findIndex((p) => p.id === id);
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    personPayments.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),
];

/**
 * Person income handlers
 */
const personIncomeHandlers = [
  http.get(`${API_BASE}/person-incomes/`, async () => {
    await delay(50);
    return HttpResponse.json([
      {
        id: 1,
        person: { id: 1, name: 'Rodrigo Souza' },
        person_id: 1,
        income_type: 'fixed_stipend',
        apartment: null,
        apartment_id: null,
        fixed_amount: 1100.0,
        start_date: '2026-01-01',
        end_date: null,
        is_active: true,
        notes: 'Estipêndio mensal',
        current_value: 1100.0,
        created_at: '2026-01-01T10:00:00Z',
        updated_at: '2026-01-01T10:00:00Z',
      },
    ]);
  }),

  http.post(`${API_BASE}/person-incomes/`, async ({ request }) => {
    await delay(100);
    const data = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 10, ...data }, { status: 201 });
  }),

  http.put(`${API_BASE}/person-incomes/:id/`, async ({ params, request }) => {
    await delay(100);
    const id = Number(params.id);
    const data = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id, ...data });
  }),

  http.delete(`${API_BASE}/person-incomes/:id/`, async () => {
    await delay(100);
    return new HttpResponse(null, { status: 204 });
  }),
];

/**
 * All handlers combined
 */
export const handlers = [
  ...buildingHandlers,
  ...furnitureHandlers,
  ...apartmentHandlers,
  ...tenantHandlers,
  ...leaseHandlers,
  ...authHandlers,
  ...dashboardHandlers,
  ...personHandlers,
  ...expenseHandlers,
  ...expenseInstallmentHandlers,
  ...financialDashboardHandlers,
  ...cashFlowHandlers,
  ...incomeHandlers,
  ...employeePaymentHandlers,
  ...personPaymentHandlers,
  ...personIncomeHandlers,
];
