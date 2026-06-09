import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';

export type IptuAlertLevel = 'warning' | 'critical';

/** One IPTU parcelamento-loss risk row — the IptuRiskRow serialized by S61 (CANON, verbatim). */
export interface IptuAlertRow {
  plan_id: number;
  external_identifier: string; // inscrição (billing_account.external_identifier)
  building_label: string; // prédio (street_number) ou "Condomínio"
  level: IptuAlertLevel;
  overdue_count: number;
  deadline: string | null; // due_date da 1ª parcela não-vencida (ISO)
  overdue_due_dates: string[]; // vencimentos das parcelas em atraso (ISO)
  message: string; // PT, montada pelo IptuAlertService
}

export interface IptuAlertsResponse {
  alerts: IptuAlertRow[];
  warning_count: number;
  critical_count: number;
}

export function useIptuAlerts() {
  return useQuery({
    queryKey: queryKeys.finances.iptuAlerts.list(),
    queryFn: async (): Promise<IptuAlertsResponse> => {
      const { data } = await apiClient.get<IptuAlertsResponse>(
        '/finances/finance-dashboard/iptu_alerts/',
      );
      // Flat object (not {results,count}) — the interceptor leaves it untouched (§8.2).
      return data;
    },
    // Uncached: depends on today_sp() + payment state; a midnight rollover / a payment must be
    // reflected on the next focus, never served stale from cache (design §9.2).
    staleTime: 0,
    refetchOnWindowFocus: true,
  });
}
