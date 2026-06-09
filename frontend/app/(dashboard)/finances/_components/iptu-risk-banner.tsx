'use client';

import { AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  type IptuAlertLevel,
  type IptuAlertRow,
  useIptuAlerts,
} from '@/lib/api/hooks/use-iptu-alerts';
import { formatDate } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

interface IptuRiskGroup {
  key: string;
  building_label: string;
  external_identifier: string;
  level: IptuAlertLevel;
  overdue_count: number;
  overdue_due_dates: string[];
  message: string;
}

/** `critical` outranks `warning` — the group level is the worst of its rows. */
function worstLevel(rows: IptuAlertRow[]): IptuAlertLevel {
  return rows.some((row) => row.level === 'critical') ? 'critical' : 'warning';
}

/** Group rows by (building_label, external_identifier); merge overdue dates, keep worst level. */
function groupByBuildingInscription(rows: IptuAlertRow[]): IptuRiskGroup[] {
  const groups = new Map<string, IptuAlertRow[]>();
  for (const row of rows) {
    const key = `${row.building_label}::${row.external_identifier}`;
    const bucket = groups.get(key) ?? [];
    bucket.push(row);
    groups.set(key, bucket);
  }
  return [...groups.entries()].map(([key, bucket]) => {
    const level = worstLevel(bucket);
    const worst = bucket.find((row) => row.level === level) ?? bucket[0];
    const dueDates = [...new Set(bucket.flatMap((row) => row.overdue_due_dates))].sort();
    const first = bucket[0];
    return {
      key,
      building_label: first?.building_label ?? '',
      external_identifier: first?.external_identifier ?? '',
      level,
      overdue_count: bucket.reduce((sum, row) => sum + row.overdue_count, 0),
      overdue_due_dates: dueDates,
      message: worst?.message ?? '',
    };
  });
}

function GroupSkeleton() {
  return (
    <div className="flex items-center justify-between rounded-lg border p-3">
      <div className="space-y-1.5">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-3 w-32" />
      </div>
      <Skeleton className="h-6 w-12" />
    </div>
  );
}

const LEVEL_STYLE: Record<IptuAlertLevel, string> = {
  warning: 'border-amber-500/30 bg-amber-500/10',
  critical: 'border-destructive/30 bg-destructive/10',
};

const LEVEL_ICON: Record<IptuAlertLevel, string> = {
  warning: 'text-amber-700 dark:text-amber-400',
  critical: 'text-destructive',
};

/**
 * IPTU parcelamento-loss risk banner (design §9.2/§10.5). Reads the flat
 * {alerts, warning_count, critical_count} object, groups by (building_label, external_identifier),
 * and renders WARNING/CRITICAL groups (status by text + icon, never colour alone). Empty → null
 * (it must NOT compete with the Atrasados KPI). Drill-down only — never a money total.
 */
export function IptuRiskBanner() {
  const { data, isLoading, error } = useIptuAlerts();

  if (isLoading) {
    return (
      <Card data-testid="iptu-risk-banner-loading">
        <CardHeader>
          <CardTitle className="text-base">Risco de IPTU</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <GroupSkeleton />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card data-testid="iptu-risk-banner-error">
        <CardHeader>
          <CardTitle className="text-base">Risco de IPTU</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-4 text-center text-muted-foreground">Erro ao carregar alertas de IPTU</p>
        </CardContent>
      </Card>
    );
  }

  if (data.alerts.length === 0) {
    return null;
  }

  const groups = groupByBuildingInscription(data.alerts);
  const hasCritical = data.critical_count > 0;

  return (
    <Card
      data-testid="iptu-risk-banner"
      className={cn(hasCritical ? 'border-destructive/30' : 'border-amber-500/30')}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <AlertTriangle
            className={cn('h-5 w-5', hasCritical ? LEVEL_ICON.critical : LEVEL_ICON.warning)}
          />
          <CardTitle className="text-base">Risco de perda de parcelamento de IPTU</CardTitle>
        </div>
        <div className="flex items-center gap-2">
          {data.critical_count > 0 && (
            <Badge variant="destructive">{data.critical_count} crítico(s)</Badge>
          )}
          {data.warning_count > 0 && (
            <Badge variant="outline" className="border-amber-500/40 text-amber-700 dark:text-amber-400">
              {data.warning_count} atenção
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {groups.map((group) => (
            <div
              key={group.key}
              className={cn('rounded-lg border p-3 transition-colors', LEVEL_STYLE[group.level])}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <AlertTriangle className={cn('h-4 w-4 shrink-0', LEVEL_ICON[group.level])} />
                    <span className="text-sm font-medium">
                      {group.external_identifier} · Prédio {group.building_label}
                    </span>
                    <Badge variant={group.level === 'critical' ? 'destructive' : 'outline'}>
                      {group.level === 'critical' ? 'Crítico' : 'Atenção'}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{group.message}</p>
                  {group.overdue_due_dates.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Parcelas vencidas:{' '}
                      {group.overdue_due_dates.map((due) => formatDate(due)).join(', ')}
                    </p>
                  )}
                </div>
                <Badge
                  variant={group.level === 'critical' ? 'destructive' : 'outline'}
                  className="shrink-0"
                >
                  {group.overdue_count}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
