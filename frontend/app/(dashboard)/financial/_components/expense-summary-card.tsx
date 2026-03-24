'use client';

import { useState } from 'react';
import {
  Briefcase,
  ChevronDown,
  ChevronRight,
  CreditCard,
  Droplets,
  Landmark,
  MoreHorizontal,
  Phone,
  Sprout,
  User,
  Wifi,
  Zap,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type {
  DashboardSummary,
  ExpenseDetail,
  PersonExpenseSummary,
  SimpleExpenseGroup,
  UtilityExpense,
} from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';
import { QuickPaymentModal } from './quick-payment-modal';

const COLLAPSED_LIMIT = 10;

type ModalData =
  | { type: 'person'; data: PersonExpenseSummary }
  | { type: 'utility'; label: string; typeKey: string; data: UtilityExpense }
  | { type: 'simple'; label: string; typeKey: string; data: SimpleExpenseGroup };

function ExpenseItem({
  label,
  icon,
  total,
  subtitle,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  total: number;
  subtitle?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center justify-between p-3 rounded-lg border',
        'hover:bg-muted/50 transition-colors cursor-pointer text-left w-full',
      )}
    >
      <div className="flex items-center gap-2.5">
        <div className="text-muted-foreground">{icon}</div>
        <div>
          <p className="text-sm font-medium">{label}</p>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
      </div>
      <span className={cn('text-sm font-semibold', total > 0 ? 'text-red-600' : 'text-muted-foreground')}>
        {formatCurrency(total)}
      </span>
    </button>
  );
}

function PersonExpenseItem({
  person,
  onClick,
}: {
  person: PersonExpenseSummary;
  onClick: () => void;
}) {
  const progress = person.total > 0 ? Math.min((person.total_paid / person.total) * 100, 100) : 0;
  const isPaid = person.pending <= 0;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'p-3 rounded-lg border text-left w-full',
        'hover:bg-muted/50 transition-colors cursor-pointer',
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">{person.person_name}</span>
        </div>
        <span className={cn('text-sm font-semibold', isPaid ? 'text-green-600' : 'text-red-600')}>
          {formatCurrency(person.total)}
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-1.5">
        <div
          className={cn(
            'h-2 rounded-full transition-all',
            isPaid ? 'bg-green-500' : progress > 50 ? 'bg-blue-500' : 'bg-amber-500',
          )}
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Pago: {formatCurrency(person.total_paid)}</span>
        <span>{isPaid ? 'Quitado' : `Restante: ${formatCurrency(person.pending)}`}</span>
      </div>
    </button>
  );
}

function CollapsibleSection({
  title,
  color,
  details,
  total,
  totalLabel,
  count,
}: {
  title: string;
  color: string;
  details: ExpenseDetail[];
  total: number;
  totalLabel: string;
  count: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const hasMore = count > COLLAPSED_LIMIT;
  const visibleItems = expanded ? details : details.slice(0, COLLAPSED_LIMIT);

  return (
    <div className="border rounded-lg">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex items-center justify-between w-full p-3 hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          <h4 className={cn('text-sm font-semibold', color)}>{title}</h4>
          <span className="text-xs text-muted-foreground">({count} itens)</span>
        </div>
        <span className={cn('text-sm font-bold', color)}>{formatCurrency(total)}</span>
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-1">
          {visibleItems.map((d, i) => (
            <div key={i} className="flex items-baseline text-sm gap-2 min-w-0">
              <span className="text-muted-foreground truncate min-w-0 flex-1">
                {d.description}
                {d.card_name ? ` (${d.card_name})` : ''}
                {d.installment ? ` — ${d.installment}` : ''}
              </span>
              <span className="font-medium whitespace-nowrap shrink-0">{formatCurrency(d.amount)}</span>
            </div>
          ))}
          {hasMore && !expanded && (
            <p className="text-xs text-muted-foreground text-center pt-1">
              ... e mais {count - COLLAPSED_LIMIT} itens
            </p>
          )}
          <div className="flex justify-between text-sm font-semibold border-t pt-1 mt-1">
            <span>{totalLabel}</span>
            <span className={color}>{formatCurrency(total)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function PersonDetailModal({
  person,
  year,
  month,
}: {
  person: PersonExpenseSummary;
  year: number;
  month: number;
}) {
  const [paymentOpen, setPaymentOpen] = useState(false);

  return (
    <div className="space-y-2">
      {person.card_total > 0 && (
        <CollapsibleSection
          title="Cartões"
          color="text-orange-600"
          details={person.card_details}
          total={person.card_total}
          totalLabel="Total cartões"
          count={person.card_details.length}
        />
      )}

      {person.loan_total > 0 && (
        <CollapsibleSection
          title="Empréstimos"
          color="text-red-600"
          details={person.loan_details}
          total={person.loan_total}
          totalLabel="Total empréstimos"
          count={person.loan_details.length}
        />
      )}

      {person.fixed_total > 0 && (
        <CollapsibleSection
          title="Despesas Fixas"
          color="text-gray-600"
          details={person.fixed_details}
          total={person.fixed_total}
          totalLabel="Total fixos"
          count={person.fixed_details.length}
        />
      )}

      {person.one_time_total > 0 && (
        <CollapsibleSection
          title="Gastos Únicos"
          color="text-blue-600"
          details={person.one_time_details}
          total={person.one_time_total}
          totalLabel="Total gastos únicos"
          count={person.one_time_details.length}
        />
      )}

      {person.offset_total > 0 && (
        <CollapsibleSection
          title="Descontos"
          color="text-green-600"
          details={person.offset_details}
          total={person.offset_total}
          totalLabel="Total descontos"
          count={person.offset_details.length}
        />
      )}

      {person.stipend_total > 0 && (
        <CollapsibleSection
          title="Estipêndios"
          color="text-purple-600"
          details={person.stipend_details}
          total={person.stipend_total}
          totalLabel="Total estipêndios"
          count={person.stipend_details.length}
        />
      )}

      {/* Total + payment info */}
      <div className="border-t-2 pt-3 mt-3 space-y-2">
        <div className="flex justify-between text-sm font-bold">
          <span>Total</span>
          <span className="text-red-600">{formatCurrency(person.total)}</span>
        </div>
        {person.is_payable && (
          <>
            {person.total_paid > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Pago</span>
                <span className="text-green-600 font-medium">{formatCurrency(person.total_paid)}</span>
              </div>
            )}
            <div className="flex justify-between text-sm font-semibold">
              <span>Pendente</span>
              <span className={person.pending <= 0 ? 'text-green-600' : 'text-red-600'}>
                {person.pending <= 0 ? 'Quitado' : formatCurrency(person.pending)}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setPaymentOpen(true)}
              className="block w-full text-center text-sm text-blue-600 hover:underline pt-1"
            >
              Registrar pagamento
            </button>
            <QuickPaymentModal
              open={paymentOpen}
              onClose={() => setPaymentOpen(false)}
              personId={person.person_id}
              personName={person.person_name}
              year={year}
              month={month}
            />
          </>
        )}
      </div>
      <a
        href={`/financial/expenses/details?type=person&id=${person.person_id}&year=${year}&month=${month}`}
        className="block text-center text-sm text-blue-600 hover:underline pt-2 border-t mt-2"
      >
        Ver detalhes completos →
      </a>
    </div>
  );
}

function UtilityDetailModal({
  data,
  utilityType,
  year,
  month,
}: {
  data: UtilityExpense;
  utilityType: string;
  year: number;
  month: number;
}) {
  return (
    <div className="space-y-2">
      {data.by_building.map((building) => (
        <div key={building.building_name} className="border rounded-lg p-3 space-y-2">
          <div className="flex justify-between items-center">
            <h4 className="text-sm font-semibold">Prédio {building.building_name}</h4>
            <span className="text-sm font-bold text-red-600">
              {formatCurrency(building.total)}
            </span>
          </div>

          {/* Bills */}
          {building.bills.map((bill, i) => {
            const hasDebt = building.debt_total > 0;
            const netAmount = hasDebt
              ? bill.amount - building.debt_total
              : bill.amount;

            return (
              <div key={i} className="space-y-1">
                {hasDebt ? (
                  <>
                    <div className="flex items-baseline text-sm gap-2 min-w-0 pl-2">
                      <span className="text-muted-foreground truncate min-w-0 flex-1">
                        Conta do mês
                      </span>
                      <span className="font-medium whitespace-nowrap shrink-0">
                        {formatCurrency(netAmount)}
                      </span>
                    </div>
                    {building.debt_installments.map((debt, j) => (
                      <div key={j} className="flex items-baseline text-sm gap-2 min-w-0 pl-2">
                        <span className="text-muted-foreground truncate min-w-0 flex-1">
                          Parcelamento dívida
                          {debt.installment ? ` (${debt.installment})` : ''}
                        </span>
                        <span className="font-medium whitespace-nowrap shrink-0">
                          {formatCurrency(debt.amount)}
                        </span>
                      </div>
                    ))}
                  </>
                ) : (
                  <div className="flex items-baseline text-sm gap-2 min-w-0 pl-2">
                    <span className="text-muted-foreground truncate min-w-0 flex-1">
                      {bill.description}
                    </span>
                    <span className="font-medium whitespace-nowrap shrink-0">
                      {formatCurrency(bill.amount)}
                    </span>
                  </div>
                )}
              </div>
            );
          })}

          {/* Standalone debt (no bill for this building) */}
          {building.bills.length === 0 && building.debt_installments.map((debt, j) => (
            <div key={j} className="flex items-baseline text-sm gap-2 min-w-0 pl-2">
              <span className="text-muted-foreground truncate min-w-0 flex-1">
                {debt.description}
                {debt.installment ? ` (${debt.installment})` : ''}
              </span>
              <span className="font-medium whitespace-nowrap shrink-0">
                {formatCurrency(debt.amount)}
              </span>
            </div>
          ))}

          {/* Notes */}
          {building.notes.map((note, j) => (
            <p key={j} className="text-xs text-amber-600 italic pl-2">
              {note}
            </p>
          ))}
        </div>
      ))}

      {data.by_building.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-2">
          Nenhuma despesa neste mês
        </p>
      )}

      {/* Grand total */}
      <div className="border-t-2 pt-3 mt-3 flex justify-between text-sm font-bold">
        <span>Total</span>
        <span className="text-red-600">{formatCurrency(data.total)}</span>
      </div>
      <a
        href={`/financial/expenses/details?type=${utilityType}&year=${year}&month=${month}`}
        className="block text-center text-sm text-blue-600 hover:underline pt-2 border-t mt-2"
      >
        Ver detalhes completos →
      </a>
    </div>
  );
}

function SimpleDetailModal({
  data,
  simpleType,
  year,
  month,
}: {
  data: SimpleExpenseGroup;
  simpleType: string;
  year: number;
  month: number;
}) {
  return (
    <div className="space-y-1">
      {data.details.map((d, i) => (
        <div key={i} className="flex items-baseline text-sm gap-2 min-w-0">
          <span className="text-muted-foreground truncate min-w-0 flex-1">
            {d.description}
          </span>
          <span className="font-medium whitespace-nowrap shrink-0">{formatCurrency(d.amount)}</span>
        </div>
      ))}
      {data.details.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-2">
          Nenhuma despesa neste mês
        </p>
      )}
      <div className="border-t-2 pt-3 mt-3 flex justify-between text-sm font-bold">
        <span>Total</span>
        <span className="text-red-600">{formatCurrency(data.total)}</span>
      </div>
      <a
        href={`/financial/expenses/details?type=${simpleType}&year=${year}&month=${month}`}
        className="block text-center text-sm text-blue-600 hover:underline pt-2 border-t mt-2"
      >
        Ver detalhes completos →
      </a>
    </div>
  );
}

export function ExpenseSummaryCard({ data, monthLabel }: { data: DashboardSummary; monthLabel: string }) {
  const [modalData, setModalData] = useState<ModalData | null>(null);
  const { expense_summary } = data;

  const modalTitle = modalData?.type === 'person'
    ? `Despesas ${modalData.data.person_name} — ${monthLabel}`
    : modalData && 'label' in modalData ? `${modalData.label} — ${monthLabel}` : '';

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <CreditCard className="h-5 w-5 text-orange-500" />
            Resumo de Despesas — {monthLabel}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
            {expense_summary.by_person.map((person) =>
              person.is_payable ? (
                <PersonExpenseItem
                  key={person.person_id}
                  person={person}
                  onClick={() => setModalData({ type: 'person', data: person })}
                />
              ) : (
                <ExpenseItem
                  key={person.person_id}
                  label={person.person_name}
                  icon={<User className="h-4 w-4" />}
                  total={person.total}
                  subtitle="Salário administração condomínio"
                  onClick={() => setModalData({ type: 'person', data: person })}
                />
              ),
            )}

            <ExpenseItem
              label="Contas de Luz"
              icon={<Zap className="h-4 w-4" />}
              total={expense_summary.electricity.total}
              subtitle={`${expense_summary.electricity.by_building.length} prédios`}
              onClick={() =>
                setModalData({
                  type: 'utility',
                  label: 'Contas de Luz',
                  typeKey: 'electricity',
                  data: expense_summary.electricity,
                })
              }
            />

            <ExpenseItem
              label="Contas de Água"
              icon={<Droplets className="h-4 w-4" />}
              total={expense_summary.water.total}
              subtitle={`${expense_summary.water.by_building.length} prédios`}
              onClick={() =>
                setModalData({
                  type: 'utility',
                  label: 'Contas de Água',
                  typeKey: 'water',
                  data: expense_summary.water,
                })
              }
            />

            <ExpenseItem
              label="IPTU"
              icon={<Landmark className="h-4 w-4" />}
              total={expense_summary.iptu.total}
              subtitle={`${expense_summary.iptu.by_building.length} prédios`}
              onClick={() =>
                setModalData({
                  type: 'utility',
                  label: 'IPTU',
                  typeKey: 'iptu',
                  data: expense_summary.iptu,
                })
              }
            />

            <ExpenseItem
              label="Internet"
              icon={<Wifi className="h-4 w-4" />}
              total={expense_summary.internet.total}
              subtitle={`${expense_summary.internet.details.length} itens`}
              onClick={() =>
                setModalData({
                  type: 'simple',
                  label: 'Internet',
                  typeKey: 'internet',
                  data: expense_summary.internet,
                })
              }
            />

            <ExpenseItem
              label="Celular / Claro"
              icon={<Phone className="h-4 w-4" />}
              total={expense_summary.celular.total}
              subtitle={`${expense_summary.celular.details.length} itens`}
              onClick={() =>
                setModalData({
                  type: 'simple',
                  label: 'Celular / Claro',
                  typeKey: 'celular',
                  data: expense_summary.celular,
                })
              }
            />

            <ExpenseItem
              label="Sítio"
              icon={<Sprout className="h-4 w-4" />}
              total={expense_summary.sitio.total}
              subtitle={`${expense_summary.sitio.details.length} itens`}
              onClick={() =>
                setModalData({
                  type: 'simple',
                  label: 'Sítio',
                  typeKey: 'sitio',
                  data: expense_summary.sitio,
                })
              }
            />

            {expense_summary.outros_fixed.total > 0 && (
              <ExpenseItem
                label="Outros"
                icon={<MoreHorizontal className="h-4 w-4" />}
                total={expense_summary.outros_fixed.total}
                subtitle={`${expense_summary.outros_fixed.details.length} itens`}
                onClick={() =>
                  setModalData({
                    type: 'simple',
                    label: 'Outros Gastos Fixos',
                    typeKey: 'outros_fixed',
                    data: expense_summary.outros_fixed,
                  })
                }
              />
            )}

            {expense_summary.employee.total > 0 && (
              <ExpenseItem
                label="Funcionários"
                icon={<Briefcase className="h-4 w-4" />}
                total={expense_summary.employee.total}
                subtitle={`${expense_summary.employee.details.length} funcionários`}
                onClick={() =>
                  setModalData({
                    type: 'simple',
                    label: 'Funcionários',
                    typeKey: 'employee',
                    data: expense_summary.employee,
                  })
                }
              />
            )}

          </div>
        </CardContent>
      </Card>

      <Dialog open={modalData !== null} onOpenChange={(open) => { if (!open) setModalData(null); }}>
        <DialogContent className="w-[calc(100vw-2rem)] max-w-2xl max-h-[80vh] overflow-y-auto overflow-x-hidden">
          <DialogHeader>
            <DialogTitle>{modalTitle}</DialogTitle>
          </DialogHeader>
          {modalData?.type === 'person' && (
            <PersonDetailModal person={modalData.data} year={data.year} month={data.month} />
          )}
          {modalData?.type === 'utility' && (
            <UtilityDetailModal
              data={modalData.data}
              utilityType={modalData.typeKey}
              year={data.year}
              month={data.month}
            />
          )}
          {modalData?.type === 'simple' && (
            <SimpleDetailModal
              data={modalData.data}
              simpleType={modalData.typeKey}
              year={data.year}
              month={data.month}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
