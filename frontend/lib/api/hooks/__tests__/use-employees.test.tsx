import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useCreateEmployee,
  useDeleteEmployee,
  useEmployees,
  useUpdateEmployee,
} from '../use-employees';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockEmployee } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

describe('useEmployees', () => {
  it('lists employees and parses base_salary to a number', async () => {
    server.use(
      http.get(`${API_BASE}/finances/employees/`, () =>
        // Raw API shape: base_salary is a string Decimal the schema transforms to number.
        HttpResponse.json([{ ...createMockEmployee(), base_salary: '1320.00' }]),
      ),
    );
    const { result } = renderHook(() => useEmployees(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    const employee = result.current.data?.[0];
    expect(typeof employee?.base_salary).toBe('number');
    expect(employee?.base_salary).toBe(1320);
  });

  it('forwards is_active / payment_type / person_id as query params', async () => {
    let captured: Record<string, string> = {};
    server.use(
      http.get(`${API_BASE}/finances/employees/`, ({ request }) => {
        const params = new URL(request.url).searchParams;
        captured = {
          is_active: params.get('is_active') ?? '',
          payment_type: params.get('payment_type') ?? '',
          person_id: params.get('person_id') ?? '',
        };
        return HttpResponse.json([]);
      }),
    );
    const { result } = renderHook(
      () => useEmployees({ is_active: true, payment_type: 'variable', person_id: 3 }),
      { wrapper: createWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(captured.is_active).toBe('true');
    expect(captured.payment_type).toBe('variable');
    expect(captured.person_id).toBe('3');
  });
});

describe('employee mutations', () => {
  it('creates a variable-only employee with base_salary null (Raymel)', async () => {
    let sentBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/finances/employees/`, async ({ request }) => {
        sentBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          createMockEmployee({
            id: 9,
            name: 'Raymel',
            payment_type: 'variable',
            base_salary: null,
          }),
          { status: 201 },
        );
      }),
    );

    const { result } = renderHook(() => useCreateEmployee(), { wrapper: createWrapper() });
    result.current.mutate({
      condominium_id: 1,
      name: 'Raymel',
      role: 'Jardineiro',
      payment_type: 'variable',
      base_salary: null,
      default_due_day: 5,
      is_active: true,
      notes: '',
      person_id: null,
      lease_id: null,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(sentBody).toHaveProperty('payment_type', 'variable');
    expect(sentBody).toHaveProperty('base_salary', null);
    expect(result.current.data?.base_salary).toBeNull();
  });

  it('creates a mixed employee linked to person + lease (Rosa-like) with _id write', async () => {
    let sentBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/finances/employees/`, async ({ request }) => {
        sentBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          createMockEmployee({
            id: 10,
            name: 'Rosa',
            payment_type: 'mixed',
            base_salary: 850,
            person: {
              id: 2,
              name: 'Rosa',
              relationship: 'Funcionária',
              phone: '',
              email: '',
              is_owner: false,
              is_employee: true,
              notes: '',
            },
          }),
          { status: 201 },
        );
      }),
    );

    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useCreateEmployee(), {
      wrapper: createWrapper(queryClient),
    });
    result.current.mutate({
      condominium_id: 1,
      name: 'Rosa',
      role: 'Faxineira',
      payment_type: 'mixed',
      base_salary: 850,
      default_due_day: 5,
      is_active: true,
      notes: '',
      person_id: 2,
      lease_id: 7,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(sentBody).toHaveProperty('person_id', 2);
    expect(sentBody).toHaveProperty('lease_id', 7);
    expect(result.current.data?.person?.name).toBe('Rosa');
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'employees'] });
  });

  it('updates an employee via PATCH stripping nested read-only objects', async () => {
    let sentBody: Record<string, unknown> | null = null;
    server.use(
      http.patch(`${API_BASE}/finances/employees/:id/`, async ({ request }) => {
        sentBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createMockEmployee({ id: 1 }));
      }),
    );
    const { result } = renderHook(() => useUpdateEmployee(), { wrapper: createWrapper() });
    result.current.mutate({
      id: 1,
      name: 'Adriana Atualizada',
      condominium: { id: 1, name: 'Condominio' },
      person: null,
      lease: null,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(sentBody).toHaveProperty('name', 'Adriana Atualizada');
    expect(sentBody).not.toHaveProperty('condominium');
    expect(sentBody).not.toHaveProperty('person');
    expect(sentBody).not.toHaveProperty('lease');
  });

  it('deletes an employee and invalidates caches', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useDeleteEmployee(), {
      wrapper: createWrapper(queryClient),
    });
    result.current.mutate(1);
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'employees'] });
  });
});
