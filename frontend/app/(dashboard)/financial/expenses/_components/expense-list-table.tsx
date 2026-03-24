import Link from 'next/link';
import {
  Briefcase,
  Droplets,
  Landmark,
  MoreHorizontal,
  Phone,
  Sprout,
  User,
  Wifi,
  Zap,
} from 'lucide-react';
import type { DashboardSummary, PersonExpenseSummary } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

interface ExpenseListTableProps {
  data: DashboardSummary;
  year: number;
  month: number;
}

type BadgeVariant = 'person' | 'condominio' | 'utility' | 'fixed' | 'salary';

const BADGE_CLASSES: Record<BadgeVariant, string> = {
  person: 'bg-info/10 text-info',
  condominio: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  utility: 'bg-warning/10 text-warning',
  fixed: 'bg-success/10 text-success',
  salary: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300',
};

const BADGE_LABELS: Record<BadgeVariant, string> = {
  person: 'Pessoa',
  condominio: 'Condomínio',
  utility: 'Utilidade',
  fixed: 'Fixo',
  salary: 'Salário',
};

function BadgeChip({ variant }: { variant: BadgeVariant }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        BADGE_CLASSES[variant],
      )}
    >
      {BADGE_LABELS[variant]}
    </span>
  );
}

function PersonProgressBar({ person }: { person: PersonExpenseSummary }) {
  const progress = person.total > 0 ? Math.min((person.total_paid / person.total) * 100, 100) : 0;
  const isPaid = person.pending <= 0;

  return (
    <div className="w-full min-w-[120px]">
      <div className="w-full bg-muted rounded-full h-2 mb-1">
        <div
          className={cn(
            'h-2 rounded-full transition-all',
            isPaid ? 'bg-success' : progress > 50 ? 'bg-info' : 'bg-warning',
          )}
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Pago: {formatCurrency(person.total_paid)}</span>
        <span>{isPaid ? 'Quitado' : `Restante: ${formatCurrency(person.pending)}`}</span>
      </div>
    </div>
  );
}

interface TableRow {
  key: string;
  icon: React.ReactNode;
  label: string;
  subtitle: string;
  badge: BadgeVariant;
  total: number;
  progressPerson: PersonExpenseSummary | null;
  href: string;
}

export function ExpenseListTable({ data, year, month }: ExpenseListTableProps) {
  const { expense_summary } = data;

  const rows: TableRow[] = [
    ...expense_summary.by_person.map((person): TableRow => ({
      key: `person-${person.person_id}`,
      icon: <User className="h-4 w-4 text-muted-foreground" />,
      label: person.person_name,
      subtitle: person.is_payable ? '' : 'Salário administração condomínio',
      badge: person.is_payable ? 'person' : 'condominio',
      total: person.total,
      progressPerson: person.is_payable ? person : null,
      href: `/financial/expenses/details?type=person&id=${person.person_id}&year=${year}&month=${month}`,
    })),
    {
      key: 'electricity',
      icon: <Zap className="h-4 w-4 text-muted-foreground" />,
      label: 'Contas de Luz',
      subtitle: `${expense_summary.electricity.by_building.length} prédios`,
      badge: 'utility',
      total: expense_summary.electricity.total,
      progressPerson: null,
      href: `/financial/expenses/details?type=electricity&year=${year}&month=${month}`,
    },
    {
      key: 'water',
      icon: <Droplets className="h-4 w-4 text-muted-foreground" />,
      label: 'Contas de Água',
      subtitle: `${expense_summary.water.by_building.length} prédios`,
      badge: 'utility',
      total: expense_summary.water.total,
      progressPerson: null,
      href: `/financial/expenses/details?type=water&year=${year}&month=${month}`,
    },
    {
      key: 'iptu',
      icon: <Landmark className="h-4 w-4 text-muted-foreground" />,
      label: 'IPTU',
      subtitle: `${expense_summary.iptu.by_building.length} prédios`,
      badge: 'utility',
      total: expense_summary.iptu.total,
      progressPerson: null,
      href: `/financial/expenses/details?type=iptu&year=${year}&month=${month}`,
    },
    {
      key: 'internet',
      icon: <Wifi className="h-4 w-4 text-muted-foreground" />,
      label: 'Internet',
      subtitle: `${expense_summary.internet.details.length} itens`,
      badge: 'fixed',
      total: expense_summary.internet.total,
      progressPerson: null,
      href: `/financial/expenses/details?type=internet&year=${year}&month=${month}`,
    },
    {
      key: 'celular',
      icon: <Phone className="h-4 w-4 text-muted-foreground" />,
      label: 'Celular / Claro',
      subtitle: `${expense_summary.celular.details.length} itens`,
      badge: 'fixed',
      total: expense_summary.celular.total,
      progressPerson: null,
      href: `/financial/expenses/details?type=celular&year=${year}&month=${month}`,
    },
    {
      key: 'sitio',
      icon: <Sprout className="h-4 w-4 text-muted-foreground" />,
      label: 'Sítio',
      subtitle: `${expense_summary.sitio.details.length} itens`,
      badge: 'fixed',
      total: expense_summary.sitio.total,
      progressPerson: null,
      href: `/financial/expenses/details?type=sitio&year=${year}&month=${month}`,
    },
    ...(expense_summary.outros_fixed.total > 0
      ? ([
          {
            key: 'outros_fixed',
            icon: <MoreHorizontal className="h-4 w-4 text-muted-foreground" />,
            label: 'Outros',
            subtitle: `${expense_summary.outros_fixed.details.length} itens`,
            badge: 'fixed' as BadgeVariant,
            total: expense_summary.outros_fixed.total,
            progressPerson: null,
            href: `/financial/expenses/details?type=outros_fixed&year=${year}&month=${month}`,
          },
        ] satisfies TableRow[])
      : []),
    ...(expense_summary.employee.total > 0
      ? ([
          {
            key: 'employee',
            icon: <Briefcase className="h-4 w-4 text-muted-foreground" />,
            label: 'Funcionários',
            subtitle: `${expense_summary.employee.details.length} funcionários`,
            badge: 'salary' as BadgeVariant,
            total: expense_summary.employee.total,
            progressPerson: null,
            href: `/financial/expenses/details?type=employee&year=${year}&month=${month}`,
          },
        ] satisfies TableRow[])
      : []),
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="pb-3 font-medium w-[280px]">Despesa</th>
            <th className="pb-3 font-medium w-[120px]">Tipo</th>
            <th className="pb-3 font-medium w-[120px] text-right pr-6">Valor</th>
            <th className="pb-3 font-medium pl-6">Progresso Pgto</th>
            <th className="pb-3 font-medium w-[120px] text-right">Ações</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map((row) => (
            <tr key={row.key} className="hover:bg-muted/30 transition-colors">
              <td className="py-3 pr-4">
                <div className="flex items-center gap-2.5">
                  {row.icon}
                  <div>
                    <p className="font-medium">{row.label}</p>
                    {row.subtitle && (
                      <p className="text-xs text-muted-foreground">{row.subtitle}</p>
                    )}
                  </div>
                </div>
              </td>
              <td className="py-3 pr-4">
                <BadgeChip variant={row.badge} />
              </td>
              <td className="py-3 pr-4 text-right">
                <span
                  className={cn(
                    'font-semibold',
                    row.total > 0 ? 'text-destructive' : 'text-muted-foreground',
                  )}
                >
                  {formatCurrency(row.total)}
                </span>
              </td>
              <td className="py-3 pr-4">
                {row.progressPerson !== null ? (
                  <PersonProgressBar person={row.progressPerson} />
                ) : (
                  <span className="text-xs text-muted-foreground">—</span>
                )}
              </td>
              <td className="py-3 text-right">
                <Link
                  href={row.href}
                  className="text-info hover:underline text-sm font-medium"
                >
                  Ver detalhes →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <p className="text-center text-muted-foreground py-8">Nenhuma despesa neste mês</p>
      )}
    </div>
  );
}
