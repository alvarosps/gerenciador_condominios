'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm, type ControllerRenderProps } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { MessageCircle, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { toast } from 'sonner';
import { useRequestOtp, useVerifyOtp } from '@/lib/api/hooks/use-tenant-auth';

export const dynamic = 'force-dynamic';

const cpfCnpjSchema = z.object({
  cpf_cnpj: z.string().min(11, 'CPF ou CNPJ é obrigatório'),
});

const otpSchema = z.object({
  code: z.string().length(6, 'O código deve ter 6 dígitos'),
});

type CpfCnpjFormData = z.infer<typeof cpfCnpjSchema>;
type OtpFormData = z.infer<typeof otpSchema>;

export default function TenantLoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<'cpf' | 'otp'>('cpf');
  const [cpfCnpj, setCpfCnpj] = useState('');

  const requestOtpMutation = useRequestOtp();
  const verifyOtpMutation = useVerifyOtp();

  const cpfForm = useForm<CpfCnpjFormData>({
    resolver: zodResolver(cpfCnpjSchema),
    defaultValues: { cpf_cnpj: '' },
  });

  const otpForm = useForm<OtpFormData>({
    resolver: zodResolver(otpSchema),
    defaultValues: { code: '' },
  });

  const handleCpfSubmit = async (values: CpfCnpjFormData) => {
    try {
      const result = await requestOtpMutation.mutateAsync({ cpf_cnpj: values.cpf_cnpj });
      setCpfCnpj(values.cpf_cnpj);
      setStep('otp');
      toast.success(result.detail ?? 'Código enviado via WhatsApp');
    } catch {
      toast.error('CPF/CNPJ não encontrado ou erro ao enviar código.');
    }
  };

  const handleOtpSubmit = async (values: OtpFormData) => {
    try {
      await verifyOtpMutation.mutateAsync({ cpf_cnpj: cpfCnpj, code: values.code });
      toast.success('Login realizado com sucesso!');
      router.push('/tenant');
    } catch {
      toast.error('Código inválido ou expirado. Tente novamente.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-primary rounded-full mx-auto mb-2">
            <MessageCircle className="h-7 w-7 text-primary-foreground" />
          </div>
          <CardTitle className="text-2xl">Portal do Inquilino</CardTitle>
          <CardDescription>
            {step === 'cpf'
              ? 'Informe seu CPF ou CNPJ para receber o código de acesso via WhatsApp'
              : 'Digite o código de 6 dígitos enviado para seu WhatsApp'}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {step === 'cpf' ? (
            <Form {...cpfForm}>
              <form onSubmit={cpfForm.handleSubmit(handleCpfSubmit)} className="space-y-4">
                <FormField
                  control={cpfForm.control}
                  name="cpf_cnpj"
                  render={({
                    field,
                  }: {
                    field: ControllerRenderProps<CpfCnpjFormData, 'cpf_cnpj'>;
                  }) => (
                    <FormItem>
                      <FormLabel>CPF ou CNPJ</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          type="text"
                          placeholder="000.000.000-00"
                          autoComplete="off"
                          className="h-11"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button
                  type="submit"
                  className="w-full h-11 font-semibold"
                  disabled={requestOtpMutation.isPending}
                >
                  {requestOtpMutation.isPending ? 'Enviando...' : 'Enviar código'}
                </Button>
              </form>
            </Form>
          ) : (
            <Form {...otpForm}>
              <form onSubmit={otpForm.handleSubmit(handleOtpSubmit)} className="space-y-4">
                <FormField
                  control={otpForm.control}
                  name="code"
                  render={({
                    field,
                  }: {
                    field: ControllerRenderProps<OtpFormData, 'code'>;
                  }) => (
                    <FormItem>
                      <FormLabel>Código de verificação</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          type="text"
                          inputMode="numeric"
                          maxLength={6}
                          placeholder="000000"
                          autoComplete="one-time-code"
                          className="h-11 text-center text-xl tracking-widest"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button
                  type="submit"
                  className="w-full h-11 font-semibold"
                  disabled={verifyOtpMutation.isPending}
                >
                  {verifyOtpMutation.isPending ? 'Verificando...' : 'Entrar'}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  className="w-full"
                  onClick={() => setStep('cpf')}
                >
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Voltar
                </Button>
              </form>
            </Form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
