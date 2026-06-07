'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCreateEmployee, useUpdateEmployee } from '@/lib/api/hooks/use-employees';
import { usePersons } from '@/lib/api/hooks/use-persons';
import { useLeases } from '@/lib/api/hooks/use-leases';
import { handleError } from '@/lib/utils/error-handler';
import {
  employeePaymentTypeValues,
  type Employee,
} from '@/lib/schemas/finances/employee.schema';
import { PAYMENT_TYPE_LABELS } from './employee-labels';
import { employeeFormSchema, type EmployeeFormValues } from './employee-form-schema';

const NONE = 'none';

function emptyDefaults(): EmployeeFormValues {
  return {
    name: '',
    role: '',
    payment_type: 'fixed',
    base_salary: 0,
    default_due_day: 5,
    is_active: true,
    person_id: null,
    lease_id: null,
    notes: '',
  };
}

function employeeToDefaults(employee: Employee): EmployeeFormValues {
  return {
    name: employee.name,
    role: employee.role ?? '',
    payment_type: employee.payment_type,
    base_salary: employee.base_salary ?? null,
    default_due_day: employee.default_due_day,
    is_active: employee.is_active,
    person_id: employee.person_id ?? employee.person?.id ?? null,
    lease_id: employee.lease_id ?? employee.lease?.id ?? null,
    notes: employee.notes ?? '',
  };
}

interface EmployeeFormModalProps {
  open: boolean;
  employee?: Employee | null;
  onClose: () => void;
}

export function EmployeeFormModal({ open, employee, onClose }: EmployeeFormModalProps) {
  const createEmployee = useCreateEmployee();
  const updateEmployee = useUpdateEmployee();
  const { data: persons } = usePersons();
  const { data: leases } = useLeases();

  const isEdit = Boolean(employee?.id);

  const form = useForm<EmployeeFormValues>({
    resolver: zodResolver(employeeFormSchema),
    defaultValues: emptyDefaults(),
  });

  useEffect(() => {
    if (open) {
      form.reset(employee ? employeeToDefaults(employee) : emptyDefaults());
    }
  }, [open, employee, form]);

  const paymentType = form.watch('payment_type');
  const showBaseSalary = paymentType === 'fixed' || paymentType === 'mixed';

  function handleSubmit(values: EmployeeFormValues) {
    const payload = {
      name: values.name,
      role: values.role,
      payment_type: values.payment_type,
      base_salary: showBaseSalary ? values.base_salary : null,
      default_due_day: values.default_due_day,
      is_active: values.is_active,
      person_id: values.person_id,
      lease_id: values.lease_id,
      notes: values.notes,
    };

    if (isEdit && employee?.id) {
      updateEmployee.mutate(
        { id: employee.id, ...payload },
        {
          onSuccess: () => {
            toast.success('Funcionário atualizado com sucesso');
            onClose();
          },
          onError: (error) => {
            handleError(error, 'Erro ao salvar funcionário');
          },
        },
      );
      return;
    }

    createEmployee.mutate(payload, {
      onSuccess: () => {
        toast.success('Funcionário criado com sucesso');
        onClose();
      },
      onError: (error) => {
        handleError(error, 'Erro ao salvar funcionário');
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Editar Funcionário' : 'Novo Funcionário'}</DialogTitle>
          <DialogDescription>
            Cadastre o funcionário e seu tipo de pagamento (fixo, variável ou misto).
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} noValidate className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nome</FormLabel>
                    <FormControl>
                      <Input placeholder="Nome do funcionário" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="role"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Cargo (opcional)</FormLabel>
                    <FormControl>
                      <Input placeholder="Ex.: Faxineira" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="payment_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tipo de pagamento</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {employeePaymentTypeValues.map((value) => (
                          <SelectItem key={value} value={value}>
                            {PAYMENT_TYPE_LABELS[value]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {showBaseSalary && (
                <FormField
                  control={form.control}
                  name="base_salary"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Salário base</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={field.value === null || Number.isNaN(field.value) ? '' : field.value}
                          onChange={(e) =>
                            field.onChange(e.target.value === '' ? null : e.target.valueAsNumber)
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              <FormField
                control={form.control}
                name="default_due_day"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Dia de pagamento</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min="1"
                        max="31"
                        value={Number.isNaN(field.value) ? '' : field.value}
                        onChange={(e) => field.onChange(e.target.valueAsNumber)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="person_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Pessoa vinculada (opcional)</FormLabel>
                    <Select
                      value={field.value ? String(field.value) : NONE}
                      onValueChange={(value) => field.onChange(value === NONE ? null : Number(value))}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Nenhuma" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value={NONE}>Nenhuma</SelectItem>
                        {persons?.map((person) =>
                          person.id === undefined ? null : (
                            <SelectItem key={person.id} value={String(person.id)}>
                              {person.name}
                            </SelectItem>
                          ),
                        )}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="lease_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Locação vinculada (opcional)</FormLabel>
                    <FormDescription>Abatimento de aluguel (Rosa).</FormDescription>
                    <Select
                      value={field.value ? String(field.value) : NONE}
                      onValueChange={(value) => field.onChange(value === NONE ? null : Number(value))}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Nenhuma" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value={NONE}>Nenhuma</SelectItem>
                        {leases?.map((lease) =>
                          lease.id === undefined ? null : (
                            <SelectItem key={lease.id} value={String(lease.id)}>
                              {lease.apartment?.number
                                ? `Apto ${lease.apartment.number}`
                                : `Locação #${String(lease.id)}`}
                            </SelectItem>
                          ),
                        )}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem className="flex items-center justify-between rounded-md border p-3">
                  <div className="space-y-0.5">
                    <FormLabel>Ativo</FormLabel>
                    <FormDescription>Funcionários inativos não geram contas mensais.</FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                      aria-label="Funcionário ativo"
                    />
                  </FormControl>
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Observações (opcional)</FormLabel>
                  <FormControl>
                    <Textarea placeholder="Notas adicionais..." rows={3} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={createEmployee.isPending || updateEmployee.isPending}>
                {isEdit ? 'Atualizar' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
