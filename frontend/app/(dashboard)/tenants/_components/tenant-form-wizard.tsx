'use client';

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Stepper } from '@/components/ui/stepper';
import {
  User,
  Phone,
  Briefcase,
  Users,
  Package,
  CheckCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { useCreateTenant, useUpdateTenant } from '@/lib/api/hooks/use-tenants';
import { useFurniture } from '@/lib/api/hooks/use-furniture';
import { Tenant } from '@/lib/schemas/tenant.schema';
import {
  validateCpfCnpj,
  formatCPFOrCNPJ,
  validateBrazilianPhone,
  formatBrazilianPhone,
  validateEmail,
} from '@/lib/utils/validators';
import { DependentFormList } from './dependent-form-list';

interface Props {
  open: boolean;
  tenant?: Tenant | null;
  onClose: () => void;
}

const MARITAL_STATUS_OPTIONS = [
  'Solteiro',
  'Casado',
  'Divorciado',
  'Viúvo',
  'União Estável',
  'Separado',
];

const tenantFormSchema = z.object({
  // Step 1: Basic Info
  name: z.string().min(3, 'Nome deve ter no mínimo 3 caracteres'),
  cpf_cnpj: z.string().refine((val) => validateCpfCnpj(val), {
    message: 'CPF/CNPJ inválido',
  }),
  is_company: z.boolean(),

  // Step 2: Contact Info
  phone: z.string().refine((val) => validateBrazilianPhone(val), {
    message: 'Telefone inválido',
  }),
  email: z
    .string()
    .optional()
    .refine((val) => !val || validateEmail(val), {
      message: 'Email inválido',
    }),
  phone_alternate: z
    .string()
    .optional()
    .refine((val) => !val || validateBrazilianPhone(val), {
      message: 'Telefone inválido',
    }),

  // Step 3: Professional Info
  profession: z.string().min(3, 'Profissão deve ter no mínimo 3 caracteres'),
  marital_status: z.string().min(1, 'Selecione o estado civil'),

  // Step 4: Dependents
  dependents: z
    .array(
      z.object({
        name: z.string(),
        phone: z.string(),
      })
    )
    .optional(),

  // Step 5: Furniture
  furniture_ids: z.array(z.number()).optional(),

  // Additional fields
  deposit_amount: z.number().nullable().optional(),
  cleaning_fee_paid: z.boolean().optional(),
  tag_deposit_paid: z.boolean().optional(),
  rent_due_day: z.number().optional(),
});

type TenantFormValues = z.infer<typeof tenantFormSchema>;

export function TenantFormWizard({ open, tenant, onClose }: Props) {
  const [currentStep, setCurrentStep] = useState(0);
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const createMutation = useCreateTenant();
  const updateMutation = useUpdateTenant();
  const { data: furniture } = useFurniture();

  const formMethods = useForm<TenantFormValues>({
    resolver: zodResolver(tenantFormSchema),
    defaultValues: {
      name: '',
      cpf_cnpj: '',
      is_company: false,
      phone: '',
      email: '',
      phone_alternate: '',
      profession: '',
      marital_status: '',
      dependents: [],
      furniture_ids: [],
      deposit_amount: null,
      cleaning_fee_paid: false,
      tag_deposit_paid: false,
      rent_due_day: 1,
    },
    mode: 'onChange',
  });

  useEffect(() => {
    if (tenant && open) {
      formMethods.reset({
        name: tenant.name,
        cpf_cnpj: tenant.cpf_cnpj,
        is_company: tenant.is_company,
        phone: tenant.phone,
        email: tenant.email || '',
        phone_alternate: tenant.phone_alternate || '',
        profession: tenant.profession || '',
        marital_status: tenant.marital_status,
        dependents: tenant.dependents || [],
        furniture_ids:
          tenant.furnitures
            ?.map((f) => f.id)
            .filter((id): id is number => id !== undefined) || [],
        deposit_amount: tenant.deposit_amount,
        cleaning_fee_paid: tenant.cleaning_fee_paid,
        tag_deposit_paid: tenant.tag_deposit_paid,
        rent_due_day: tenant.rent_due_day,
      });
    } else if (!tenant && open) {
      formMethods.reset();
      setCurrentStep(0);
    }
  }, [tenant, formMethods, open]);

  const steps = [
    {
      title: 'Dados Básicos',
      icon: <User className="h-5 w-5" />,
      description: 'Nome e documento',
    },
    {
      title: 'Contato',
      icon: <Phone className="h-5 w-5" />,
      description: 'Telefone e email',
    },
    {
      title: 'Profissão',
      icon: <Briefcase className="h-5 w-5" />,
      description: 'Informações profissionais',
    },
    {
      title: 'Dependentes',
      icon: <Users className="h-5 w-5" />,
      description: 'Dependentes do inquilino',
    },
    {
      title: 'Móveis',
      icon: <Package className="h-5 w-5" />,
      description: 'Móveis do inquilino',
    },
    {
      title: 'Revisão',
      icon: <CheckCircle className="h-5 w-5" />,
      description: 'Conferir dados',
    },
  ];

  const handleNext = async () => {
    const stepFields = getStepFields(currentStep);
    let isValid = true;

    if (stepFields.length > 0) {
      // Trigger validation for step fields
      for (const field of stepFields) {
        const result = await formMethods.trigger(field as keyof TenantFormValues);
        if (!result) isValid = false;
      }
    }

    if (isValid) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrev = () => {
    setCurrentStep(currentStep - 1);
  };

  const handleSubmit = async () => {
    try {
      const values = formMethods.getValues();

      // Remove empty optional fields and add required defaults
      const cleanedData = {
        ...values,
        email: values.email || undefined,
        phone_alternate: values.phone_alternate || undefined,
        dependents:
          values.dependents?.filter(
            (d: { name: string; phone: string }) => d.name && d.phone
          ) || [],
        deposit_amount: values.deposit_amount || null,
        cleaning_fee_paid: values.cleaning_fee_paid || false,
        tag_deposit_paid: values.tag_deposit_paid || false,
        rent_due_day: values.rent_due_day || 1,
      };

      if (tenant?.id) {
        await updateMutation.mutateAsync({
          ...cleanedData,
          id: tenant.id,
        });
        toast.success('Inquilino atualizado com sucesso');
      } else {
        await createMutation.mutateAsync(cleanedData);
        toast.success('Inquilino criado com sucesso');
      }

      onClose();
      formMethods.reset();
      setCurrentStep(0);
    } catch (error) {
      toast.error('Erro ao salvar inquilino');
      console.error('Save error:', error);
    }
  };

  const handleCancelClick = () => {
    setShowCancelDialog(true);
  };

  const handleCancelConfirm = () => {
    setShowCancelDialog(false);
    onClose();
    formMethods.reset();
    setCurrentStep(0);
  };

  const getStepFields = (step: number): string[] => {
    switch (step) {
      case 0:
        return ['name', 'cpf_cnpj', 'is_company'];
      case 1:
        return ['phone', 'email', 'phone_alternate'];
      case 2:
        return ['profession', 'marital_status'];
      case 3:
        return []; // Dependents are optional
      case 4:
        return []; // Furniture is optional
      case 5:
        return []; // Review step
      default:
        return [];
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return renderBasicInfoStep();
      case 1:
        return renderContactInfoStep();
      case 2:
        return renderProfessionalInfoStep();
      case 3:
        return renderDependentsStep();
      case 4:
        return renderFurnitureStep();
      case 5:
        return renderReviewStep();
      default:
        return null;
    }
  };

  const renderBasicInfoStep = () => (
    <div className="space-y-6">
      <FormField
        control={formMethods.control}
        name="name"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Nome / Razão Social *</FormLabel>
            <FormControl>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Nome completo ou razão social"
                  className="pl-10"
                  {...field}
                />
              </div>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={formMethods.control}
        name="is_company"
        render={({ field }) => (
          <FormItem className="space-y-3">
            <FormLabel>Tipo de Pessoa *</FormLabel>
            <FormControl>
              <RadioGroup
                onValueChange={(value) => field.onChange(value === 'true')}
                value={String(field.value)}
                className="flex gap-4"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="false" id="person-false" />
                  <label
                    htmlFor="person-false"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                  >
                    Pessoa Física
                  </label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="true" id="person-true" />
                  <label
                    htmlFor="person-true"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                  >
                    Pessoa Jurídica
                  </label>
                </div>
              </RadioGroup>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={formMethods.control}
        name="cpf_cnpj"
        render={({ field }) => (
          <FormItem>
            <FormLabel>CPF / CNPJ *</FormLabel>
            <FormControl>
              <Input
                placeholder="000.000.000-00 ou 00.000.000/0000-00"
                maxLength={18}
                {...field}
                onChange={(e) => {
                  const formatted = formatCPFOrCNPJ(e.target.value);
                  field.onChange(formatted);
                }}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );

  const renderContactInfoStep = () => (
    <div className="space-y-6">
      <FormField
        control={formMethods.control}
        name="phone"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Telefone Principal *</FormLabel>
            <FormControl>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="(00) 00000-0000"
                  maxLength={15}
                  className="pl-10"
                  {...field}
                  onChange={(e) => {
                    const formatted = formatBrazilianPhone(e.target.value);
                    field.onChange(formatted);
                  }}
                />
              </div>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={formMethods.control}
        name="phone_alternate"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Telefone Alternativo (opcional)</FormLabel>
            <FormControl>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="(00) 00000-0000"
                  maxLength={15}
                  className="pl-10"
                  {...field}
                  onChange={(e) => {
                    const formatted = formatBrazilianPhone(e.target.value);
                    field.onChange(formatted);
                  }}
                />
              </div>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={formMethods.control}
        name="email"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Email (opcional)</FormLabel>
            <FormControl>
              <Input
                type="email"
                placeholder="email@exemplo.com"
                {...field}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );

  const renderProfessionalInfoStep = () => (
    <div className="space-y-6">
      <FormField
        control={formMethods.control}
        name="profession"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Profissão *</FormLabel>
            <FormControl>
              <div className="relative">
                <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Ex: Engenheiro, Professor, Médico"
                  className="pl-10"
                  {...field}
                />
              </div>
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={formMethods.control}
        name="marital_status"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Estado Civil *</FormLabel>
            <Select onValueChange={field.onChange} value={field.value}>
              <FormControl>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione o estado civil" />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                {MARITAL_STATUS_OPTIONS.map((status) => (
                  <SelectItem key={status} value={status}>
                    {status}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );

  const renderDependentsStep = () => (
    <div>
      <div className="mb-6">
        <h3 className="text-lg font-medium">Dependentes</h3>
        <p className="text-sm text-muted-foreground">
          Adicione os dependentes que morarão no apartamento (opcional)
        </p>
      </div>
      <DependentFormList formMethods={formMethods} />
    </div>
  );

  const renderFurnitureStep = () => (
    <div>
      <div className="mb-6">
        <h3 className="text-lg font-medium">Móveis do Inquilino</h3>
        <p className="text-sm text-muted-foreground">
          Selecione os móveis que o inquilino possui e levará para o apartamento (opcional)
        </p>
      </div>
      <FormField
        control={formMethods.control}
        name="furniture_ids"
        render={() => (
          <FormItem>
            <div className="grid grid-cols-2 gap-4">
              {furniture?.map((item) => (
                <FormField
                  key={item.id}
                  control={formMethods.control}
                  name="furniture_ids"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                      <FormControl>
                        <Checkbox
                          checked={field.value?.includes(item.id!)}
                          onCheckedChange={(checked) => {
                            const current = field.value || [];
                            if (checked) {
                              field.onChange([...current, item.id!]);
                            } else {
                              field.onChange(
                                current.filter((id) => id !== item.id)
                              );
                            }
                          }}
                        />
                      </FormControl>
                      <FormLabel className="font-normal cursor-pointer">
                        {item.name}
                      </FormLabel>
                    </FormItem>
                  )}
                />
              ))}
            </div>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );

  const renderReviewStep = () => {
    const values = formMethods.getValues();

    return (
      <div>
        <div className="mb-6">
          <h3 className="text-lg font-medium">Revise os Dados</h3>
          <p className="text-sm text-muted-foreground">
            Confira todas as informações antes de salvar
          </p>
        </div>

        <Card className="mb-4">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Dados Básicos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div>
                <strong>Nome:</strong> {values.name}
              </div>
              <div>
                <strong>Tipo:</strong>{' '}
                {values.is_company ? 'Pessoa Jurídica' : 'Pessoa Física'}
              </div>
              <div>
                <strong>CPF/CNPJ:</strong> {formatCPFOrCNPJ(values.cpf_cnpj || '')}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="mb-4">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Contato</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div>
                <strong>Telefone:</strong> {formatBrazilianPhone(values.phone || '')}
              </div>
              {values.phone_alternate && (
                <div>
                  <strong>Tel. Alternativo:</strong>{' '}
                  {formatBrazilianPhone(values.phone_alternate)}
                </div>
              )}
              {values.email && (
                <div>
                  <strong>Email:</strong> {values.email}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="mb-4">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Informações Profissionais</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div>
                <strong>Profissão:</strong> {values.profession}
              </div>
              <div>
                <strong>Estado Civil:</strong> {values.marital_status}
              </div>
            </div>
          </CardContent>
        </Card>

        {values.dependents && values.dependents.length > 0 && (
          <Card className="mb-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                Dependentes ({values.dependents.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {values.dependents.map(
                  (dep: { name: string; phone: string }, index: number) => (
                    <div key={index} className="text-sm pl-4 border-l-2 border-primary">
                      <div>
                        <strong>{dep.name}</strong>
                      </div>
                      <div className="text-muted-foreground">
                        {formatBrazilianPhone(dep.phone)}
                      </div>
                    </div>
                  )
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {values.furniture_ids && values.furniture_ids.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                Móveis ({values.furniture_ids.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm">
                {furniture
                  ?.filter((f) => values.furniture_ids?.includes(f.id!))
                  .map((f) => f.name)
                  .join(', ')}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  };

  return (
    <>
      <Dialog open={open} onOpenChange={() => {}}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {tenant ? 'Editar Inquilino' : 'Novo Inquilino'}
            </DialogTitle>
          </DialogHeader>

          <Stepper steps={steps} currentStep={currentStep} className="mt-4 mb-8" />

          <Form {...formMethods}>
            <div className="min-h-[400px]">{renderStepContent()}</div>
          </Form>

          <Separator className="my-4" />

          <DialogFooter className="flex justify-between sm:justify-between">
            <div>
              {currentStep > 0 && (
                <Button variant="outline" onClick={handlePrev}>
                  Voltar
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleCancelClick}>
                Cancelar
              </Button>
              {currentStep < steps.length - 1 && (
                <Button onClick={handleNext}>Próximo</Button>
              )}
              {currentStep === steps.length - 1 && (
                <Button
                  onClick={handleSubmit}
                  disabled={
                    createMutation.isPending || updateMutation.isPending
                  }
                >
                  {tenant ? 'Atualizar' : 'Criar'} Inquilino
                </Button>
              )}
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Descartar alterações?</AlertDialogTitle>
            <AlertDialogDescription>
              Os dados preenchidos serão perdidos.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Continuar editando</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCancelConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Sim, descartar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
