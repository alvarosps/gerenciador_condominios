import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { useRentCalendar, useToggleRentPayment } from '../use-rent-calendar';
import type { RentCalendar } from '../use-rent-calendar';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { queryKeys } from '@/lib/api/query-keys';
import { createMockRentCalendar, createMockRentCalendarItem } from '@/tests/mocks/data/rent-calendar';

const API_BASE = 'http://localhost:8008/api';

describe('useRentCalendar', () => {
  it('should fetch the rent calendar for a given year and month', async () => {
    const { result } = renderHook(() => useRentCalendar(2026, 6), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.year).toBe(2026);
    expect(result.current.data?.month).toBe(6);
    expect(result.current.data?.today).toBeDefined();
    expect(result.current.data?.days).toBeDefined();
    expect(result.current.data?.stats).toBeDefined();

    const stats = result.current.data?.stats;
    expect(stats?.received_total).toBeDefined();
    expect(stats?.to_receive_total).toBeDefined();
    expect(stats?.expected_total).toBeDefined();
    expect(stats?.paid_count).toBeDefined();
    expect(stats?.due_count).toBeDefined();
    expect(stats?.overdue_count).toBeDefined();
    expect(stats?.overdue_total_fee).toBeDefined();
    expect(stats?.vacant_kitnets_count).toBeDefined();
    expect(stats?.vacant_kitnets_value).toBeDefined();

    const firstItem = result.current.data?.days?.[0]?.items?.[0];
    expect(firstItem?.lease_id).toBeDefined();
    expect(firstItem?.is_paid).toBe(false);
    expect(firstItem?.can_toggle).toBe(true);
    expect(firstItem?.late_fee).toBeDefined();
  });

  it('should forward building_id to the query string when provided', async () => {
    server.use(
      http.get(`${API_BASE}/dashboard/rent_calendar/`, ({ request }) => {
        const buildingId = new URL(request.url).searchParams.get('building_id');
        return HttpResponse.json(
          createMockRentCalendar({
            days: [
              {
                day: 5,
                date: '2026-06-05',
                weekday: 'Sexta',
                items: [createMockRentCalendarItem({ building_number: buildingId ?? 'none' })],
              },
            ],
          }),
        );
      }),
    );

    const { result } = renderHook(() => useRentCalendar(2026, 6, 1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.days?.[0]?.items?.[0]?.building_number).toBe('1');
  });

  it('should handle error from server', async () => {
    server.use(
      http.get(`${API_BASE}/dashboard/rent_calendar/`, () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useRentCalendar(2026, 6), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

function seedCalendarHandler() {
  // The GET handler populates the cache via the real query path; a mounted useRentCalendar
  // keeps the cache entry alive (gcTime:0 would collect manually-seeded data without an observer).
  server.use(
    http.get(`${API_BASE}/dashboard/rent_calendar/`, () => {
      return HttpResponse.json(
        createMockRentCalendar({
          days: [
            {
              day: 5,
              date: '2026-06-05',
              weekday: 'Sexta',
              items: [createMockRentCalendarItem({ lease_id: 12, is_paid: false })],
            },
          ],
        }),
      );
    }),
  );
}

describe('useToggleRentPayment', () => {
  it('should optimistically flip is_paid before the request settles', async () => {
    seedCalendarHandler();
    const queryClient = createTestQueryClient();

    const { result } = renderHook(
      () => ({
        calendar: useRentCalendar(2026, 6),
        toggle: useToggleRentPayment(),
      }),
      { wrapper: createWrapper(queryClient) },
    );

    await waitFor(() => expect(result.current.calendar.isSuccess).toBe(true), { timeout: 5000 });

    server.use(
      http.post(`${API_BASE}/dashboard/toggle_rent_payment/`, async () => {
        await delay(200);
        return HttpResponse.json({
          status: 'paid',
          is_paid: true,
          message: 'Aluguel marcado como pago',
        });
      }),
    );

    result.current.toggle.mutate({ lease_id: 12, reference_month: '2026-06-01' });

    await waitFor(() => {
      const snapshot = queryClient.getQueryData<RentCalendar>(
        queryKeys.rentCalendar.month(2026, 6),
      );
      expect(snapshot?.days?.[0]?.items?.[0]?.is_paid).toBe(true);
    });

    await waitFor(() => expect(result.current.toggle.isSuccess).toBe(true), { timeout: 5000 });
  });

  it('should roll back the optimistic flip when the request errors', async () => {
    // First GET (initial load) returns is_paid:false immediately; any later GET (the onSettled
    // refetch) returns is_paid:true but delayed, opening a window where the only false value can
    // come from the rollback (onError restoring the snapshot), not from the refetch masking it.
    let getCount = 0;
    server.use(
      http.get(`${API_BASE}/dashboard/rent_calendar/`, async () => {
        getCount += 1;
        const isRefetch = getCount > 1;
        if (isRefetch) {
          await delay(200);
        }
        return HttpResponse.json(
          createMockRentCalendar({
            days: [
              {
                day: 5,
                date: '2026-06-05',
                weekday: 'Sexta',
                items: [createMockRentCalendarItem({ lease_id: 12, is_paid: isRefetch })],
              },
            ],
          }),
        );
      }),
    );
    const queryClient = createTestQueryClient();

    const { result } = renderHook(
      () => ({
        calendar: useRentCalendar(2026, 6),
        toggle: useToggleRentPayment(),
      }),
      { wrapper: createWrapper(queryClient) },
    );

    await waitFor(() => expect(result.current.calendar.isSuccess).toBe(true), { timeout: 5000 });

    server.use(
      http.post(`${API_BASE}/dashboard/toggle_rent_payment/`, async () => {
        await delay(100);
        return new HttpResponse(null, { status: 500 });
      }),
    );

    result.current.toggle.mutate({ lease_id: 12, reference_month: '2026-06-01' });

    await waitFor(() => expect(result.current.toggle.isError).toBe(true), { timeout: 5000 });

    // onError already rolled the optimistic flip back to false. The onSettled refetch (delayed)
    // has not resolved yet, so this window observes the restored snapshot — not the refetch.
    await waitFor(() => {
      const snapshot = queryClient.getQueryData<RentCalendar>(
        queryKeys.rentCalendar.month(2026, 6),
      );
      expect(snapshot?.days?.[0]?.items?.[0]?.is_paid).toBe(false);
    });

    // Let the delayed onSettled refetch settle so no request is left in flight at teardown.
    await waitFor(() => {
      const snapshot = queryClient.getQueryData<RentCalendar>(
        queryKeys.rentCalendar.month(2026, 6),
      );
      expect(snapshot?.days?.[0]?.items?.[0]?.is_paid).toBe(true);
    });
  });

  it('should invalidate rentCalendar, latePaymentSummary and financialSummary on settle', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useToggleRentPayment(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({ lease_id: 12, reference_month: '2026-06-01' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['rent-calendar'] });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['dashboard', 'late_payment_summary'],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['dashboard', 'financial_summary'] });
  });
});
