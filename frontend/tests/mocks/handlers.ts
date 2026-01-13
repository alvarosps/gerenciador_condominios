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
  createMockBuilding,
  createMockFurniture,
  createMockApartment,
  createMockTenant,
  createMockLease,
} from './data';

const API_BASE = 'http://localhost:8000/api';

// Mutable copies for CRUD operations during tests
let buildings = [...mockBuildings];
let furniture = [...mockFurniture];
let apartments = [...mockApartments];
let tenants = [...mockTenants];
let leases = [...mockLeases];

// Helper to reset data between tests
export function resetMockData() {
  buildings = [...mockBuildings];
  furniture = [...mockFurniture];
  apartments = [...mockApartments];
  tenants = [...mockTenants];
  leases = [...mockLeases];
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
    leases[index].contract_generated = true;
    leases[index].pdf_path = `contracts/mock/contract_${id}.pdf`;
    return HttpResponse.json({
      message: 'Contract generated successfully',
      pdf_path: leases[index].pdf_path,
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
    const dailyRate = lease.rental_value / 30;
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
    const oldDueDay = leases[index].due_day;
    leases[index].due_day = data.new_due_day;
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
    const totalRevenue = leases.reduce((sum, l) => sum + l.rental_value, 0);
    return HttpResponse.json({
      total_revenue: totalRevenue,
      avg_rental_value: leases.length > 0 ? totalRevenue / leases.length : 0,
      total_cleaning_fees: leases.reduce((sum, l) => sum + (l.cleaning_fee || 0), 0),
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
];
