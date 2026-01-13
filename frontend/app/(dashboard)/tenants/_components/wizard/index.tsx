'use client';

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  User,
  Phone,
  Briefcase,
  Users,
  Package,
  CheckCircle,
} from 'lucide-react';
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
import { Form } from '@/components/ui/form';
import { Separator } from '@/components/ui/separator';
import { Stepper } from '@/components/ui/stepper';
import { toast } from 'sonner';
import { useCreateTenant, useUpdateTenant } from '@/lib/api/hooks/use-tenants';
import { Tenant } from '@/lib/schemas/tenant.schema';
import { tenantFormSchema, TenantFormValues, WIZARD_STEPS } from './types';
import { BasicInfoStep } from './basic-info-step';
import { ContactInfoStep } from './contact-info-step';
import { ProfessionalInfoStep } from './professional-info-step';
import { DependentsStep } from './dependents-step';
import { FurnitureStep } from './furniture-step';
import { ReviewStep } from './review-step';

interface Props {
  open: boolean;
  tenant?: Tenant | null;
  onClose: () => void;
}

const STEP_ICONS = [
  <User key="user" className="h-5 w-5" />,
  <Phone key="phone" className="h-5 w-5" />,
  <Briefcase key="briefcase" className="h-5 w-5" />,
  <Users key="users" className="h-5 w-5" />,
  <Package key="package" className="h-5 w-5" />,
  <CheckCircle key="check" className="h-5 w-5" />,
];

export function TenantFormWizard({ open, tenant, onClose }: Props) {
  const [currentStep, setCurrentStep] = useState(0);
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const createMutation = useCreateTenant();
  const updateMutation = useUpdateTenant();

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

  const steps = WIZARD_STEPS.map((step, index) => ({
    ...step,
    icon: STEP_ICONS[index],
  }));

  const handleNext = async () => {
    const stepFields = WIZARD_STEPS[currentStep].fields;
    let isValid = true;

    if (stepFields.length > 0) {
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

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return <BasicInfoStep formMethods={formMethods} />;
      case 1:
        return <ContactInfoStep formMethods={formMethods} />;
      case 2:
        return <ProfessionalInfoStep formMethods={formMethods} />;
      case 3:
        return <DependentsStep formMethods={formMethods} />;
      case 4:
        return <FurnitureStep formMethods={formMethods} />;
      case 5:
        return <ReviewStep formMethods={formMethods} />;
      default:
        return null;
    }
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
