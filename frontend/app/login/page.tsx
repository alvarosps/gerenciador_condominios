'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm, ControllerRenderProps } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Mail, Lock, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { toast } from 'sonner';
import { useLogin, useGoogleLogin } from '@/lib/api/hooks/use-auth';

// Force dynamic rendering to prevent static generation issues
export const dynamic = 'force-dynamic';

/**
 * Login form validation schema
 */
const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(6, 'Senha deve ter no mínimo 6 caracteres'),
});

type LoginFormData = z.infer<typeof loginSchema>;

/**
 * Login page component
 * Provides JWT authentication and Google OAuth options
 */
export default function LoginPage() {
  const router = useRouter();
  const loginMutation = useLogin();
  const googleLogin = useGoogleLogin();
  const [error, setError] = useState<string | null>(null);

  // Initialize form with react-hook-form + zod validation
  const form = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  /**
   * Handle form submission
   */
  const handleSubmit = async (values: LoginFormData) => {
    try {
      setError(null);

      // Attempt login
      await loginMutation.mutateAsync(values);

      toast.success('Login realizado com sucesso!');
      router.push('/dashboard');
    } catch (err) {
      if (err instanceof z.ZodError) {
        toast.error('Por favor, preencha todos os campos corretamente');
      } else {
        setError('Credenciais inválidas. Verifique seu email e senha.');
      }
    }
  };

  /**
   * Handle Google OAuth login
   */
  const handleGoogleLogin = () => {
    googleLogin();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <Card className="w-full max-w-md shadow-xl">
        <CardContent className="pt-6">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-primary rounded-full mb-4">
              <User className="h-8 w-8 text-primary-foreground" />
            </div>
            <h1 className="text-3xl font-bold text-gray-800">Condomínios Manager</h1>
            <p className="text-muted-foreground mt-2">Sistema de Gestão de Locações</p>
          </div>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription className="flex items-start justify-between">
                <span>{error}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 hover:bg-transparent"
                  onClick={() => setError(null)}
                >
                  <span className="sr-only">Fechar</span>
                  <span aria-hidden="true">×</span>
                </Button>
              </AlertDescription>
            </Alert>
          )}

          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }: { field: ControllerRenderProps<LoginFormData, 'email'> }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Mail className="absolute left-3 top-3 h-5 w-5 text-muted-foreground" />
                        <Input
                          {...field}
                          type="email"
                          placeholder="seu@email.com"
                          autoComplete="email"
                          className="pl-10 h-11"
                        />
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }: { field: ControllerRenderProps<LoginFormData, 'password'> }) => (
                  <FormItem>
                    <FormLabel>Senha</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Lock className="absolute left-3 top-3 h-5 w-5 text-muted-foreground" />
                        <Input
                          {...field}
                          type="password"
                          placeholder="••••••••"
                          autoComplete="current-password"
                          className="pl-10 h-11"
                        />
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button
                type="submit"
                className="w-full h-11 font-semibold"
                disabled={loginMutation.isPending}
              >
                {loginMutation.isPending ? 'Entrando...' : 'Entrar'}
              </Button>
            </form>
          </Form>

          <div className="relative my-6">
            <Separator />
            <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-card px-2 text-sm text-muted-foreground">
              ou
            </span>
          </div>

          <Button
            variant="outline"
            onClick={handleGoogleLogin}
            className="w-full h-11 font-semibold"
          >
            <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Entrar com Google
          </Button>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            <p>Ainda não tem uma conta?</p>
            <Button
              variant="link"
              className="p-0 h-auto font-normal"
              onClick={() => router.push('/register')}
            >
              Criar nova conta
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
