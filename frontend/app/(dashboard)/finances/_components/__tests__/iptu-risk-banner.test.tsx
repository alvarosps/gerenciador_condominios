import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockIptuAlertRow } from '@/tests/mocks/data/finances';
import { IptuRiskBanner } from '../iptu-risk-banner';

const API_BASE = 'http://localhost:8008/api';

function setAlerts(
  alerts: ReturnType<typeof createMockIptuAlertRow>[],
  warningCount: number,
  criticalCount: number,
) {
  server.use(
    http.get(`${API_BASE}/finances/finance-dashboard/iptu_alerts/`, () =>
      HttpResponse.json({
        alerts,
        warning_count: warningCount,
        critical_count: criticalCount,
      }),
    ),
  );
}

describe('IptuRiskBanner', () => {
  it('renders nothing when there are no alerts', async () => {
    setAlerts([], 0, 0);
    const { container } = renderWithProviders(<IptuRiskBanner />, {
      queryClient: createTestQueryClient(),
    });

    // Wait for the loading skeleton to clear; an empty response collapses the banner to null.
    await waitFor(() => {
      expect(container.querySelector('[data-testid="iptu-risk-banner-loading"]')).toBeNull();
    });
    expect(container.querySelector('[data-testid="iptu-risk-banner"]')).toBeNull();
    expect(screen.queryByText(/parcelamento de IPTU/i)).not.toBeInTheDocument();
  });

  it('renders a WARNING group with the building_label, external_identifier and overdue due dates', async () => {
    setAlerts(
      [
        createMockIptuAlertRow({
          level: 'warning',
          external_identifier: '1.273.798.010-05',
          building_label: '836',
          overdue_count: 1,
          overdue_due_dates: ['2026-05-10'],
          message: 'IPTU 1.273.798.010-05 (836): 1 parcela atrasada (venc. 10/05).',
        }),
      ],
      1,
      0,
    );

    renderWithProviders(<IptuRiskBanner />, { queryClient: createTestQueryClient() });

    // The inscrição appears both in the group header and inside the PT message.
    expect((await screen.findAllByText(/1\.273\.798\.010-05/)).length).toBeGreaterThan(0);
    expect(screen.getByText(/Prédio 836/)).toBeInTheDocument();
    expect(screen.getByText(/10\/05\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/1 parcela atrasada/)).toBeInTheDocument();
  });

  it('renders a CRITICAL group when overdue_count >= 2 (distinct visual from warning)', async () => {
    setAlerts(
      [
        createMockIptuAlertRow({
          level: 'critical',
          external_identifier: '999',
          building_label: '850',
          overdue_count: 2,
          overdue_due_dates: ['2026-04-10', '2026-05-10'],
          message: 'IPTU 999 (850): 2 parcelas atrasadas — parcelamento perdido.',
        }),
      ],
      0,
      1,
    );

    renderWithProviders(<IptuRiskBanner />, { queryClient: createTestQueryClient() });

    expect(await screen.findByText(/parcelamento perdido/i)).toBeInTheDocument();
    // CRITICAL uses a distinct destructive style (not the amber warning class).
    const banner = screen.getByTestId('iptu-risk-banner');
    expect(banner.className).toMatch(/destructive/);
  });

  it('groups multiple rows by (building_label, external_identifier) and shows the worst level per group', async () => {
    setAlerts(
      [
        createMockIptuAlertRow({
          plan_id: 1,
          level: 'warning',
          external_identifier: '555',
          building_label: '836',
          overdue_count: 1,
          overdue_due_dates: ['2026-05-10'],
          message: 'IPTU 555 (836): 1 parcela atrasada.',
        }),
        createMockIptuAlertRow({
          plan_id: 2,
          level: 'critical',
          external_identifier: '555',
          building_label: '836',
          overdue_count: 2,
          overdue_due_dates: ['2026-03-10', '2026-04-10'],
          message: 'IPTU 555 (836): 2 parcelas atrasadas — parcelamento perdido.',
        }),
      ],
      1,
      1,
    );

    renderWithProviders(<IptuRiskBanner />, { queryClient: createTestQueryClient() });

    await screen.findByText(/parcelamento perdido/i);
    // A single group for (836, 555) at the worst level (critical), listing all overdue dates.
    expect(screen.getAllByText(/555/).length).toBeGreaterThan(0);
    expect(screen.getByText(/10\/03\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/10\/04\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/10\/05\/2026/)).toBeInTheDocument();
  });

  it('does not render a money total (drill-down, not a second Atrasados total)', async () => {
    setAlerts(
      [
        createMockIptuAlertRow({
          level: 'warning',
          overdue_count: 1,
          overdue_due_dates: ['2026-05-10'],
          message: 'IPTU 123 (836): 1 parcela atrasada.',
        }),
      ],
      1,
      0,
    );

    renderWithProviders(<IptuRiskBanner />, { queryClient: createTestQueryClient() });

    await screen.findByTestId('iptu-risk-banner');
    expect(screen.queryByText(/R\$/)).not.toBeInTheDocument();
  });
});
