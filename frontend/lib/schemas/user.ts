import { z } from 'zod';

export const userFormSchema = z.object({
  username: z.string().min(1, 'Nome de usuário é obrigatório'),
  email: z.email('Email inválido').or(z.literal('')),
  first_name: z.string(),
  last_name: z.string(),
  is_staff: z.boolean(),
  is_active: z.boolean(),
  password: z.string().min(8, 'Senha deve ter no mínimo 8 caracteres').or(z.literal('')),
});

export type UserFormValues = z.infer<typeof userFormSchema>;

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  is_active: boolean;
  date_joined: string;
}
