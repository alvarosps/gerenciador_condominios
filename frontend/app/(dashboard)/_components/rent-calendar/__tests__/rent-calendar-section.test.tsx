import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse, delay } from 'msw';
import { renderWithProviders, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import {
  createMockRentCalendar,
  createMockRentCalendarItem,
} from '@/tests/mocks/data/rent-calendar';
import { RentCalendarSection } from '../rent-calendar-section';

const API_BASE = 'http://localhost:8008/api';

// The section derives (year, month) from the real current date. Echo whatever it
// requests and put the item on the same day as `today` so the default-selected day
// (today's day) shows it — keeps the test independent of the real calendar date.
function serveCalendar(opts: { isPaid?: boolean } = {}) {
  server.use(
    http.get(`${API_BASE}/dashboard/rent_calendar/`, ({ request }) => {
      const url = new URL(request.url);
      const year = Number(url.searchParams.get('year'));
      const month = Number(url.searchParams.get('month'));
      const mm = String(month).padStart(2, '0');
      const date = `${String(year)}-${mm}-05`;
      return HttpResponse.json(
        createMockRentCalendar({
          year,
          month,
          today: date,
          next_due_date: date,
          days: [
            {
              day: 5,
              date,
              weekday: 'Sexta',
              items: [createMockRentCalendarItem({ lease_id: 12, is_paid: opts.isPaid ?? false })],
            },
          ],
        }),
      );
    }),
    http.get(`${API_BASE}/buildings/`, () => HttpResponse.json([])),
  );
}

describe('RentCalendarSection', () => {
  it('renders the day panel, month grid and stats from the API', async () => {
    serveCalendar();
    renderWithProviders(<RentCalendarSection />, { queryClient: createTestQueryClient() });

    // Column 1 — day panel item
    expect(await screen.findByText('Apto 101 · Préd. 836')).toBeInTheDocument();
    // Column 2 — month grid weekday header
    expect(screen.getByText('Dom')).toBeInTheDocument();
    // Column 3 — stats
    expect(screen.getByText('Recebido até hoje')).toBeInTheDocument();
  });

  it('shows a skeleton while the calendar is loading', () => {
    server.use(
      http.get(`${API_BASE}/dashboard/rent_calendar/`, async () => {
        await delay(100);
        return HttpResponse.json(createMockRentCalendar());
      }),
      http.get(`${API_BASE}/buildings/`, () => HttpResponse.json([])),
    );
    const { container } = renderWithProviders(<RentCalendarSection />, {
      queryClient: createTestQueryClient(),
    });
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('optimistically marks rent as paid when the toggle is clicked', async () => {
    serveCalendar({ isPaid: false });
    server.use(
      http.post(`${API_BASE}/dashboard/toggle_rent_payment/`, async () => {
        await delay(150);
        return HttpResponse.json({
          status: 'paid',
          is_paid: true,
          message: 'Aluguel marcado como pago.',
        });
      }),
    );
    renderWithProviders(<RentCalendarSection />, { queryClient: createTestQueryClient() });

    const toggle = await screen.findByRole('switch');
    expect(toggle).toHaveAttribute('aria-checked', 'false');

    await userEvent.click(toggle);

    // The optimistic update flips the cached item -> the day panel now shows "Pago".
    expect(await screen.findByText('Pago')).toBeInTheDocument();
  });
});
