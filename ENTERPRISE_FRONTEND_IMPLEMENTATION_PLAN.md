# Enterprise Frontend Implementation Plan
## Condomínios Manager - Zero-Defect Quality Standard

**Project Type:** Enterprise Property Management System
**Quality Requirement:** Zero errors, zero warnings, production-grade code
**Timeline:** 10 weeks
**Team Approach:** Multi-agent orchestration with specialized experts

---

## Executive Summary

This plan outlines the complete implementation of an enterprise-level frontend application for Condomínios Manager. The current Django backend (100% functional) will be integrated with a modern Next.js 14 frontend built to the highest quality standards.

**Zero-Defect Strategy:**
- TypeScript strict mode (compile-time safety)
- Zod runtime validation (runtime safety)
- Pre-commit hooks (prevent bad code from entering repository)
- Comprehensive test suite (80%+ coverage)
- CI/CD quality gates (automated enforcement)
- Multi-layer code review (automated + human)

---

## Technology Stack

### Core Framework
- **Next.js 14** (App Router) - Production-ready React framework with SSR, routing, optimization
- **React 18** - Latest React with concurrent features
- **TypeScript 5+** (strict mode) - Type safety at compile time

### State Management & Data Fetching
- **TanStack Query v5** - Server state management, caching, synchronization
- **Zustand** - Minimal client state (user preferences, UI state)

### UI & Styling
- **Ant Design v5** - Enterprise-grade component library
- **Tailwind CSS** - Utility-first styling for custom components
- **Recharts** - Data visualization and charts

### Forms & Validation
- **React Hook Form** - Performant form handling
- **Zod** - Schema validation (runtime + TypeScript integration)

### Code Quality Tools
- **ESLint** - Code linting (strict rules, zero warnings allowed)
- **Prettier** - Code formatting
- **Husky** - Git hooks for pre-commit checks
- **Commitlint** - Conventional commit messages
- **lint-staged** - Run linters on staged files only

### Testing
- **Vitest** - Unit testing framework (faster than Jest)
- **React Testing Library** - Component testing
- **Playwright** - E2E testing
- **MSW (Mock Service Worker)** - API mocking for tests

### Additional Tools
- **Monaco Editor** - Code editor for contract template editing
- **xlsx** - Excel export functionality
- **date-fns** - Date manipulation
- **react-pdf** - PDF preview
- **axios** - HTTP client with interceptors

---

## Project Structure

```
/frontend
├── app/                                  # Next.js 14 App Router
│   ├── layout.tsx                       # Root layout
│   ├── page.tsx                         # Landing/login page
│   ├── (dashboard)/                     # Dashboard route group
│   │   ├── layout.tsx                   # Dashboard layout with sidebar
│   │   ├── page.tsx                     # Dashboard home
│   │   ├── buildings/                   # Buildings module
│   │   │   ├── page.tsx                 # List view
│   │   │   ├── [id]/                    # Detail/edit view
│   │   │   ├── new/                     # Create view
│   │   │   └── _components/             # Module-specific components
│   │   ├── apartments/                  # Apartments module
│   │   │   ├── page.tsx
│   │   │   ├── [id]/
│   │   │   ├── new/
│   │   │   └── _components/
│   │   ├── tenants/                     # Tenants module
│   │   │   ├── page.tsx
│   │   │   ├── [id]/
│   │   │   ├── new/
│   │   │   └── _components/
│   │   ├── leases/                      # Leases module
│   │   │   ├── page.tsx
│   │   │   ├── [id]/
│   │   │   ├── new/
│   │   │   └── _components/
│   │   ├── furniture/                   # Furniture module
│   │   │   └── page.tsx
│   │   └── contract-template/           # Template editor
│   │       └── page.tsx
│   └── api/                             # API routes (proxy to Django)
│       └── [...path]/
│           └── route.ts
├── components/
│   ├── ui/                              # Reusable UI components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── modal.tsx
│   │   ├── table.tsx
│   │   ├── card.tsx
│   │   └── ...
│   ├── forms/                           # Form components
│   │   ├── form-wrapper.tsx
│   │   ├── form-field.tsx
│   │   └── form-modal.tsx
│   ├── tables/                          # Table components
│   │   ├── data-table.tsx
│   │   ├── table-filters.tsx
│   │   └── table-actions.tsx
│   ├── layouts/                         # Layout components
│   │   ├── main-layout.tsx
│   │   ├── sidebar.tsx
│   │   └── header.tsx
│   └── shared/                          # Shared components
│       ├── loading.tsx
│       ├── error-boundary.tsx
│       └── confirm-dialog.tsx
├── lib/
│   ├── api/                             # API client
│   │   ├── client.ts                    # Axios instance with interceptors
│   │   ├── hooks/                       # TanStack Query hooks
│   │   │   ├── use-buildings.ts
│   │   │   ├── use-apartments.ts
│   │   │   ├── use-tenants.ts
│   │   │   ├── use-leases.ts
│   │   │   └── use-furniture.ts
│   │   └── endpoints/                   # API endpoint definitions
│   │       ├── buildings.ts
│   │       ├── apartments.ts
│   │       └── ...
│   ├── schemas/                         # Zod validation schemas
│   │   ├── building.schema.ts
│   │   ├── apartment.schema.ts
│   │   ├── tenant.schema.ts
│   │   ├── lease.schema.ts
│   │   └── furniture.schema.ts
│   ├── types/                           # TypeScript types
│   │   └── index.ts
│   ├── utils/                           # Utility functions
│   │   ├── formatters.ts                # Currency, date, CPF formatters
│   │   ├── validators.ts                # CPF/CNPJ validation
│   │   ├── constants.ts                 # App constants
│   │   └── helpers.ts                   # Helper functions
│   └── config/                          # Configuration
│       ├── query-client.ts              # TanStack Query config
│       └── theme.ts                     # Ant Design theme
├── hooks/                               # Custom React hooks
│   ├── use-local-storage.ts
│   ├── use-debounce.ts
│   ├── use-pagination.ts
│   └── use-filters.ts
├── store/                               # Zustand stores
│   ├── ui-store.ts                      # UI state (sidebar, theme)
│   └── user-store.ts                    # User preferences
├── tests/                               # Test files
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── public/                              # Static assets
│   ├── images/
│   └── icons/
├── .github/
│   └── workflows/
│       ├── ci.yml                       # CI pipeline
│       └── deploy.yml                   # Deployment pipeline
├── .husky/                              # Git hooks
│   ├── pre-commit
│   └── commit-msg
├── .vscode/                             # VS Code settings
│   └── settings.json
├── .eslintrc.json                       # ESLint configuration
├── .prettierrc                          # Prettier configuration
├── tsconfig.json                        # TypeScript configuration
├── next.config.js                       # Next.js configuration
├── tailwind.config.ts                   # Tailwind configuration
├── vitest.config.ts                     # Vitest configuration
├── playwright.config.ts                 # Playwright configuration
├── package.json
└── README.md
```

---

## Phase-by-Phase Implementation

### Phase 1: Foundation & Infrastructure (Week 1)

**Goal:** Set up project with quality gates and reusable components

**Agent:** `nextjs-architecture-expert`, `typescript-pro`

#### Tasks:

1. **Project Initialization**
   ```bash
   npx create-next-app@latest frontend --typescript --tailwind --app --src-dir=false
   cd frontend
   ```

2. **Install Dependencies**
   ```bash
   # Core
   npm install antd @ant-design/icons @tanstack/react-query zustand zod
   npm install react-hook-form @hookform/resolvers axios date-fns
   npm install @monaco-editor/react xlsx recharts

   # Dev Dependencies
   npm install -D @types/node eslint prettier eslint-config-prettier
   npm install -D husky lint-staged @commitlint/cli @commitlint/config-conventional
   npm install -D vitest @testing-library/react @testing-library/jest-dom
   npm install -D @playwright/test msw
   ```

3. **Configure TypeScript (tsconfig.json)**
   ```json
   {
     "compilerOptions": {
       "target": "ES2022",
       "lib": ["dom", "dom.iterable", "esnext"],
       "allowJs": true,
       "skipLibCheck": true,
       "strict": true,
       "noImplicitAny": true,
       "strictNullChecks": true,
       "noUnusedLocals": true,
       "noUnusedParameters": true,
       "noImplicitReturns": true,
       "forceConsistentCasingInFileNames": true,
       "esModuleInterop": true,
       "module": "esnext",
       "moduleResolution": "bundler",
       "resolveJsonModule": true,
       "isolatedModules": true,
       "jsx": "preserve",
       "incremental": true,
       "plugins": [{ "name": "next" }],
       "paths": {
         "@/*": ["./*"]
       }
     }
   }
   ```

4. **Configure ESLint (.eslintrc.json)**
   ```json
   {
     "extends": [
       "next/core-web-vitals",
       "plugin:@typescript-eslint/recommended",
       "plugin:@typescript-eslint/recommended-requiring-type-checking",
       "prettier"
     ],
     "rules": {
       "no-console": "warn",
       "no-unused-vars": "error",
       "@typescript-eslint/no-explicit-any": "error",
       "@typescript-eslint/explicit-function-return-type": "warn",
       "react/no-unescaped-entities": "error",
       "react-hooks/rules-of-hooks": "error",
       "react-hooks/exhaustive-deps": "warn"
     }
   }
   ```

5. **Configure Prettier (.prettierrc)**
   ```json
   {
     "semi": true,
     "trailingComma": "es5",
     "singleQuote": true,
     "printWidth": 100,
     "tabWidth": 2,
     "useTabs": false
   }
   ```

6. **Set up Husky & lint-staged**
   ```bash
   npx husky init
   ```

   **.husky/pre-commit:**
   ```bash
   #!/usr/bin/env sh
   . "$(dirname -- "$0")/_/husky.sh"

   npx lint-staged
   npm run type-check
   npm run test:unit
   ```

   **package.json (lint-staged):**
   ```json
   {
     "lint-staged": {
       "*.{ts,tsx}": [
         "eslint --fix",
         "prettier --write",
         "vitest related --run"
       ]
     }
   }
   ```

7. **Create Base Components**
   - `components/layouts/main-layout.tsx` - Main dashboard layout
   - `components/layouts/sidebar.tsx` - Navigation sidebar
   - `components/layouts/header.tsx` - Top header with search
   - `components/ui/loading.tsx` - Loading spinner
   - `components/ui/error-boundary.tsx` - Error boundary
   - `components/tables/data-table.tsx` - Reusable table with pagination, sorting, filtering
   - `components/forms/form-modal.tsx` - Reusable modal for create/edit

8. **Configure TanStack Query**
   ```typescript
   // lib/config/query-client.ts
   import { QueryClient } from '@tanstack/react-query';

   export const queryClient = new QueryClient({
     defaultOptions: {
       queries: {
         staleTime: 1000 * 60 * 5, // 5 minutes
         retry: 3,
         refetchOnWindowFocus: false,
       },
     },
   });
   ```

9. **Set up Ant Design Theme**
   ```typescript
   // app/layout.tsx
   import { ConfigProvider } from 'antd';
   import ptBR from 'antd/locale/pt_BR';

   const theme = {
     token: {
       colorPrimary: '#1890ff',
       borderRadius: 6,
     },
   };

   export default function RootLayout({ children }) {
     return (
       <html lang="pt-BR">
         <body>
           <ConfigProvider locale={ptBR} theme={theme}>
             {children}
           </ConfigProvider>
         </body>
       </html>
     );
   }
   ```

10. **Create API Client**
    ```typescript
    // lib/api/client.ts
    import axios from 'axios';

    export const apiClient = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    apiClient.interceptors.request.use((config) => {
      // Add auth token if exists
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor
    apiClient.interceptors.response.use(
      (response) => response,
      (error) => {
        // Global error handling
        if (error.response?.status === 401) {
          // Redirect to login
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
    ```

11. **Create Zod Schemas**
    ```typescript
    // lib/schemas/building.schema.ts
    import { z } from 'zod';

    export const buildingSchema = z.object({
      id: z.number().optional(),
      street_number: z.number().positive('Número deve ser positivo'),
      name: z.string().min(1, 'Nome é obrigatório'),
      address: z.string().min(1, 'Endereço é obrigatório'),
    });

    export type Building = z.infer<typeof buildingSchema>;
    ```

12. **Set up CI/CD Pipeline**
    ```yaml
    # .github/workflows/ci.yml
    name: CI

    on:
      pull_request:
      push:
        branches: [main, develop]

    jobs:
      quality:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3
          - uses: actions/setup-node@v3
            with:
              node-version: '20'
              cache: 'npm'

          - name: Install dependencies
            run: npm ci

          - name: Type check
            run: npm run type-check

          - name: Lint
            run: npm run lint

          - name: Format check
            run: npm run format:check

          - name: Unit tests
            run: npm run test:unit

          - name: Build
            run: npm run build
    ```

**Deliverables:**
- ✅ Next.js project configured with TypeScript strict mode
- ✅ All quality tools installed and configured
- ✅ Pre-commit hooks preventing bad code
- ✅ CI/CD pipeline enforcing quality gates
- ✅ Base layout and navigation structure
- ✅ Reusable components (table, modal, forms)
- ✅ API client with interceptors
- ✅ TanStack Query configured
- ✅ Zod schemas created

**Quality Metrics:**
- TypeScript strict mode: ✅ Enabled
- ESLint warnings: 0
- Prettier formatting: ✅ Consistent
- Test coverage: N/A (no features yet)
- Build success: ✅

---

### Phase 2: Buildings & Furniture Modules (Week 2)

**Goal:** Complete CRUD for Buildings and Furniture with full test coverage

**Agents:** `frontend-developer`, `test-engineer`, `code-reviewer`

#### Buildings Module

1. **Create API Hooks**
   ```typescript
   // lib/api/hooks/use-buildings.ts
   import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
   import { apiClient } from '../client';
   import { Building, buildingSchema } from '@/lib/schemas/building.schema';

   export function useBuildings() {
     return useQuery({
       queryKey: ['buildings'],
       queryFn: async () => {
         const { data } = await apiClient.get<Building[]>('/buildings/');
         return data.map((b) => buildingSchema.parse(b));
       },
     });
   }

   export function useCreateBuilding() {
     const queryClient = useQueryClient();
     return useMutation({
       mutationFn: async (data: Omit<Building, 'id'>) => {
         const validated = buildingSchema.omit({ id: true }).parse(data);
         const response = await apiClient.post('/buildings/', validated);
         return response.data;
       },
       onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['buildings'] });
       },
     });
   }

   export function useUpdateBuilding() {
     const queryClient = useQueryClient();
     return useMutation({
       mutationFn: async ({ id, ...data }: Building) => {
         const validated = buildingSchema.parse({ id, ...data });
         const response = await apiClient.put(`/buildings/${id}/`, validated);
         return response.data;
       },
       onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['buildings'] });
       },
     });
   }

   export function useDeleteBuilding() {
     const queryClient = useQueryClient();
     return useMutation({
       mutationFn: async (id: number) => {
         await apiClient.delete(`/buildings/${id}/`);
       },
       onSuccess: () => {
         queryClient.invalidateQueries({ queryKey: ['buildings'] });
       },
     });
   }
   ```

2. **Create Buildings List Page**
   ```typescript
   // app/(dashboard)/buildings/page.tsx
   'use client';

   import { useState } from 'react';
   import { Button, message } from 'antd';
   import { PlusOutlined } from '@ant-design/icons';
   import { DataTable } from '@/components/tables/data-table';
   import { BuildingFormModal } from './_components/building-form-modal';
   import { useBuildings, useDeleteBuilding } from '@/lib/api/hooks/use-buildings';
   import { Building } from '@/lib/schemas/building.schema';

   export default function BuildingsPage() {
     const [isModalOpen, setIsModalOpen] = useState(false);
     const [editingBuilding, setEditingBuilding] = useState<Building | null>(null);

     const { data: buildings, isLoading } = useBuildings();
     const deleteMutation = useDeleteBuilding();

     const columns = [
       {
         title: 'Número',
         dataIndex: 'street_number',
         key: 'street_number',
         sorter: true,
       },
       {
         title: 'Nome',
         dataIndex: 'name',
         key: 'name',
         sorter: true,
       },
       {
         title: 'Endereço',
         dataIndex: 'address',
         key: 'address',
       },
       {
         title: 'Ações',
         key: 'actions',
         render: (_: unknown, record: Building) => (
           <>
             <Button onClick={() => handleEdit(record)}>Editar</Button>
             <Button danger onClick={() => handleDelete(record.id!)}>
               Excluir
             </Button>
           </>
         ),
       },
     ];

     const handleEdit = (building: Building) => {
       setEditingBuilding(building);
       setIsModalOpen(true);
     };

     const handleDelete = async (id: number) => {
       try {
         await deleteMutation.mutateAsync(id);
         message.success('Prédio excluído com sucesso');
       } catch (error) {
         message.error('Erro ao excluir prédio');
       }
     };

     return (
       <div>
         <div className="mb-4 flex justify-between">
           <h1 className="text-2xl font-bold">Prédios</h1>
           <Button
             type="primary"
             icon={<PlusOutlined />}
             onClick={() => setIsModalOpen(true)}
           >
             Novo Prédio
           </Button>
         </div>

         <DataTable
           columns={columns}
           dataSource={buildings}
           loading={isLoading}
           rowKey="id"
         />

         <BuildingFormModal
           open={isModalOpen}
           building={editingBuilding}
           onClose={() => {
             setIsModalOpen(false);
             setEditingBuilding(null);
           }}
         />
       </div>
     );
   }
   ```

3. **Create Building Form Modal**
   ```typescript
   // app/(dashboard)/buildings/_components/building-form-modal.tsx
   import { useEffect } from 'react';
   import { Modal, Form, Input, InputNumber, message } from 'antd';
   import { useCreateBuilding, useUpdateBuilding } from '@/lib/api/hooks/use-buildings';
   import { Building, buildingSchema } from '@/lib/schemas/building.schema';

   interface Props {
     open: boolean;
     building?: Building | null;
     onClose: () => void;
   }

   export function BuildingFormModal({ open, building, onClose }: Props) {
     const [form] = Form.useForm();
     const createMutation = useCreateBuilding();
     const updateMutation = useUpdateBuilding();

     useEffect(() => {
       if (building) {
         form.setFieldsValue(building);
       } else {
         form.resetFields();
       }
     }, [building, form]);

     const handleSubmit = async () => {
       try {
         const values = await form.validateFields();
         const validated = buildingSchema.parse(values);

         if (building?.id) {
           await updateMutation.mutateAsync({ ...validated, id: building.id });
           message.success('Prédio atualizado com sucesso');
         } else {
           await createMutation.mutateAsync(validated);
           message.success('Prédio criado com sucesso');
         }

         onClose();
         form.resetFields();
       } catch (error) {
         message.error('Erro ao salvar prédio');
       }
     };

     return (
       <Modal
         title={building ? 'Editar Prédio' : 'Novo Prédio'}
         open={open}
         onOk={handleSubmit}
         onCancel={onClose}
         confirmLoading={createMutation.isPending || updateMutation.isPending}
       >
         <Form form={form} layout="vertical">
           <Form.Item
             name="street_number"
             label="Número da Rua"
             rules={[{ required: true, message: 'Campo obrigatório' }]}
           >
             <InputNumber min={1} className="w-full" />
           </Form.Item>

           <Form.Item
             name="name"
             label="Nome do Prédio"
             rules={[{ required: true, message: 'Campo obrigatório' }]}
           >
             <Input />
           </Form.Item>

           <Form.Item
             name="address"
             label="Endereço"
             rules={[{ required: true, message: 'Campo obrigatório' }]}
           >
             <Input.TextArea rows={3} />
           </Form.Item>
         </Form>
       </Modal>
     );
   }
   ```

4. **Create Unit Tests**
   ```typescript
   // app/(dashboard)/buildings/__tests__/buildings.test.tsx
   import { render, screen, waitFor } from '@testing-library/react';
   import userEvent from '@testing-library/user-event';
   import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
   import { http, HttpResponse } from 'msw';
   import { setupServer } from 'msw/node';
   import BuildingsPage from '../page';

   const server = setupServer(
     http.get('/api/buildings/', () => {
       return HttpResponse.json([
         { id: 1, street_number: 836, name: 'Prédio A', address: 'Rua X' },
       ]);
     })
   );

   beforeAll(() => server.listen());
   afterEach(() => server.resetHandlers());
   afterAll(() => server.close());

   test('renders buildings list', async () => {
     const queryClient = new QueryClient();
     render(
       <QueryClientProvider client={queryClient}>
         <BuildingsPage />
       </QueryClientProvider>
     );

     await waitFor(() => {
       expect(screen.getByText('Prédio A')).toBeInTheDocument();
     });
   });

   test('opens modal when clicking new building', async () => {
     const user = userEvent.setup();
     const queryClient = new QueryClient();

     render(
       <QueryClientProvider client={queryClient}>
         <BuildingsPage />
       </QueryClientProvider>
     );

     const newButton = screen.getByText('Novo Prédio');
     await user.click(newButton);

     expect(screen.getByText('Novo Prédio')).toBeInTheDocument();
   });
   ```

#### Furniture Module

Implement same pattern as Buildings:
- API hooks (use-furniture.ts)
- List page with DataTable
- Form modal for create/edit
- Unit tests

**Deliverables:**
- ✅ Buildings CRUD complete with tests
- ✅ Furniture CRUD complete with tests
- ✅ All API hooks implemented
- ✅ Data table component working
- ✅ Form validation with Zod
- ✅ Error handling and loading states
- ✅ 80%+ test coverage

**Quality Metrics:**
- ESLint warnings: 0
- TypeScript errors: 0
- Test coverage: 80%+
- All tests passing: ✅

---

### Phase 3: Apartments Module (Week 3)

**Goal:** Complete apartment management with building and furniture relationships

**Agents:** `frontend-developer`, `test-engineer`

#### Key Features:
- List apartments with building names
- Filter by building, rental status, price range
- Create/edit with building dropdown
- Furniture multi-select (checkboxes)
- Rental status badges (Available/Rented)
- Currency formatting for prices
- Date pickers for lease dates

#### Implementation:

1. **Apartment Schema**
   ```typescript
   // lib/schemas/apartment.schema.ts
   import { z } from 'zod';

   export const apartmentSchema = z.object({
     id: z.number().optional(),
     building_id: z.number().positive('Selecione um prédio'),
     building: z.object({
       id: z.number(),
       street_number: z.number(),
       name: z.string(),
       address: z.string(),
     }).optional(),
     number: z.number().positive('Número deve ser positivo'),
     interfone_configured: z.boolean().default(false),
     contract_generated: z.boolean().default(false),
     contract_signed: z.boolean().default(false),
     rental_value: z.number().positive('Valor deve ser positivo'),
     cleaning_fee: z.number().min(0, 'Valor não pode ser negativo').default(0),
     max_tenants: z.number().positive('Deve ter pelo menos 1 inquilino'),
     is_rented: z.boolean().default(false),
     lease_date: z.string().nullable().optional(),
     last_rent_increase_date: z.string().nullable().optional(),
     furnitures: z.array(z.object({
       id: z.number(),
       name: z.string(),
     })).default([]),
     furniture_ids: z.array(z.number()).optional(),
   });

   export type Apartment = z.infer<typeof apartmentSchema>;
   ```

2. **Apartment Form with Furniture Selection**
   ```typescript
   // app/(dashboard)/apartments/_components/apartment-form-modal.tsx
   import { Form, InputNumber, Select, Checkbox, DatePicker } from 'antd';
   import { useBuildings } from '@/lib/api/hooks/use-buildings';
   import { useFurniture } from '@/lib/api/hooks/use-furniture';
   import { formatCurrency } from '@/lib/utils/formatters';

   export function ApartmentFormModal({ ... }) {
     const { data: buildings } = useBuildings();
     const { data: furniture } = useFurniture();

     return (
       <Modal ...>
         <Form form={form} layout="vertical">
           <Form.Item name="building_id" label="Prédio" rules={[...]}>
             <Select
               showSearch
               options={buildings?.map((b) => ({
                 value: b.id,
                 label: `${b.name} - ${b.street_number}`,
               }))}
             />
           </Form.Item>

           <Form.Item name="number" label="Número do Apartamento" rules={[...]}>
             <InputNumber min={1} />
           </Form.Item>

           <Form.Item name="rental_value" label="Valor do Aluguel" rules={[...]}>
             <InputNumber
               min={0}
               precision={2}
               formatter={(value) => formatCurrency(value)}
               parser={(value) => value?.replace(/\D/g, '')}
             />
           </Form.Item>

           <Form.Item name="max_tenants" label="Máximo de Inquilinos" rules={[...]}>
             <InputNumber min={1} />
           </Form.Item>

           <Form.Item name="furniture_ids" label="Móveis do Apartamento">
             <Checkbox.Group
               options={furniture?.map((f) => ({
                 label: f.name,
                 value: f.id,
               }))}
             />
           </Form.Item>
         </Form>
       </Modal>
     );
   }
   ```

3. **Apartment List with Filters**
   ```typescript
   // app/(dashboard)/apartments/page.tsx
   import { useState } from 'react';
   import { Select, Input, Tag } from 'antd';
   import { DataTable } from '@/components/tables/data-table';
   import { formatCurrency } from '@/lib/utils/formatters';

   export default function ApartmentsPage() {
     const [filters, setFilters] = useState({
       building_id: null,
       is_rented: null,
       min_price: null,
       max_price: null,
     });

     const columns = [
       {
         title: 'Prédio',
         dataIndex: ['building', 'name'],
         render: (name: string, record: Apartment) => (
           `${name} - ${record.building.street_number}`
         ),
       },
       {
         title: 'Apartamento',
         dataIndex: 'number',
       },
       {
         title: 'Valor',
         dataIndex: 'rental_value',
         render: (value: number) => formatCurrency(value),
       },
       {
         title: 'Status',
         dataIndex: 'is_rented',
         render: (isRented: boolean) => (
           <Tag color={isRented ? 'red' : 'green'}>
             {isRented ? 'Alugado' : 'Disponível'}
           </Tag>
         ),
       },
       // ... more columns
     ];

     return (
       <div>
         <FilterPanel filters={filters} onChange={setFilters} />
         <DataTable ... />
       </div>
     );
   }
   ```

**Deliverables:**
- ✅ Apartments CRUD complete
- ✅ Building relationship working
- ✅ Furniture multi-select working
- ✅ Advanced filters implemented
- ✅ Currency formatting
- ✅ Status badges
- ✅ 80%+ test coverage

---

### Phase 4: Tenants Module (Week 4)

**Goal:** Complete tenant management with dependents and validation

**Agents:** `frontend-developer`, `test-engineer`

#### Key Features:
- Multi-step wizard for tenant creation
- CPF/CNPJ validation (checksum algorithm)
- Brazilian phone formatting
- Dependent management (add/edit/remove)
- Tenant furniture selection
- Person vs Company handling

#### Implementation:

1. **CPF/CNPJ Validator**
   ```typescript
   // lib/utils/validators.ts
   export function validateCPF(cpf: string): boolean {
     const cleanCPF = cpf.replace(/\D/g, '');
     if (cleanCPF.length !== 11) return false;

     // Check if all digits are the same
     if (/^(\d)\1{10}$/.test(cleanCPF)) return false;

     // Validate checksum
     let sum = 0;
     for (let i = 0; i < 9; i++) {
       sum += parseInt(cleanCPF.charAt(i)) * (10 - i);
     }
     let checkDigit = 11 - (sum % 11);
     if (checkDigit >= 10) checkDigit = 0;
     if (checkDigit !== parseInt(cleanCPF.charAt(9))) return false;

     sum = 0;
     for (let i = 0; i < 10; i++) {
       sum += parseInt(cleanCPF.charAt(i)) * (11 - i);
     }
     checkDigit = 11 - (sum % 11);
     if (checkDigit >= 10) checkDigit = 0;
     if (checkDigit !== parseInt(cleanCPF.charAt(10))) return false;

     return true;
   }

   export function validateCNPJ(cnpj: string): boolean {
     // Similar implementation for CNPJ validation
     // ...
   }

   export function formatCPF(cpf: string): string {
     const clean = cpf.replace(/\D/g, '');
     return clean.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
   }

   export function formatPhone(phone: string): string {
     const clean = phone.replace(/\D/g, '');
     return clean.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
   }
   ```

2. **Tenant Multi-Step Form**
   ```typescript
   // app/(dashboard)/tenants/_components/tenant-form-wizard.tsx
   import { Steps, Form, Button } from 'antd';
   import { useState } from 'react';

   export function TenantFormWizard() {
     const [currentStep, setCurrentStep] = useState(0);
     const [formData, setFormData] = useState({});

     const steps = [
       {
         title: 'Dados Básicos',
         content: <BasicInfoStep />,
       },
       {
         title: 'Dados Pessoais',
         content: <PersonalInfoStep />,
       },
       {
         title: 'Dados Financeiros',
         content: <FinancialInfoStep />,
       },
       {
         title: 'Móveis',
         content: <FurnitureStep />,
       },
       {
         title: 'Dependentes',
         content: <DependentsStep />,
       },
       {
         title: 'Revisão',
         content: <ReviewStep data={formData} />,
       },
     ];

     const handleNext = async () => {
       const values = await form.validateFields();
       setFormData({ ...formData, ...values });
       setCurrentStep(currentStep + 1);
     };

     return (
       <div>
         <Steps current={currentStep} items={steps} />
         <div className="mt-8">
           {steps[currentStep].content}
         </div>
         <div className="mt-4">
           {currentStep > 0 && (
             <Button onClick={() => setCurrentStep(currentStep - 1)}>
               Voltar
             </Button>
           )}
           {currentStep < steps.length - 1 && (
             <Button type="primary" onClick={handleNext}>
               Próximo
             </Button>
           )}
           {currentStep === steps.length - 1 && (
             <Button type="primary" onClick={handleSubmit}>
               Finalizar
             </Button>
           )}
         </div>
       </div>
     );
   }
   ```

3. **Dependents Management**
   ```typescript
   // app/(dashboard)/tenants/_components/dependents-step.tsx
   import { Form, Input, Button, List } from 'antd';
   import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';

   export function DependentsStep() {
     const [dependents, setDependents] = useState([]);

     const addDependent = () => {
       const newDependent = {
         id: Date.now(),
         name: '',
         phone: '',
       };
       setDependents([...dependents, newDependent]);
     };

     const removeDependent = (id: number) => {
       setDependents(dependents.filter(d => d.id !== id));
     };

     return (
       <div>
         <Button
           icon={<PlusOutlined />}
           onClick={addDependent}
           className="mb-4"
         >
           Adicionar Dependente
         </Button>

         <List
           dataSource={dependents}
           renderItem={(dep) => (
             <List.Item
               actions={[
                 <Button
                   danger
                   icon={<DeleteOutlined />}
                   onClick={() => removeDependent(dep.id)}
                 />,
               ]}
             >
               <Form.Item label="Nome" className="flex-1">
                 <Input
                   value={dep.name}
                   onChange={(e) => updateDependent(dep.id, 'name', e.target.value)}
                 />
               </Form.Item>
               <Form.Item label="Telefone" className="flex-1">
                 <Input
                   value={dep.phone}
                   onChange={(e) => updateDependent(dep.id, 'phone', e.target.value)}
                 />
               </Form.Item>
             </List.Item>
           )}
         />
       </div>
     );
   }
   ```

**Deliverables:**
- ✅ Tenant CRUD with wizard
- ✅ CPF/CNPJ validation working
- ✅ Phone formatting
- ✅ Dependent management
- ✅ Person/Company toggle
- ✅ 80%+ test coverage

---

### Phase 5: Leases Module (Week 5)

**Goal:** Complete lease management with contract generation

**Agents:** `frontend-developer`, `test-engineer`

#### Key Features:
- Lease creation wizard (6 steps)
- Apartment availability check
- Tenant count validation
- Automatic fee calculation
- Furniture calculation display
- Contract PDF generation
- Late fee calculator
- Due date changer

#### Implementation:

1. **Lease Creation Wizard - Step 1: Select Apartment**
   ```typescript
   // app/(dashboard)/leases/_components/wizard-steps/select-apartment.tsx
   import { Select, Card, Tag } from 'antd';
   import { useApartments } from '@/lib/api/hooks/use-apartments';

   export function SelectApartmentStep({ value, onChange }) {
     const { data: apartments } = useApartments();

     // Filter only available apartments
     const availableApartments = apartments?.filter(a => !a.is_rented);

     const selectedApartment = apartments?.find(a => a.id === value);

     return (
       <div>
         <Form.Item
           label="Selecione o Apartamento"
           rules={[{ required: true }]}
         >
           <Select
             value={value}
             onChange={onChange}
             options={availableApartments?.map(a => ({
               value: a.id,
               label: `Apto ${a.number} - ${a.building.name} (${a.building.street_number})`,
             }))}
           />
         </Form.Item>

         {selectedApartment && (
           <Card title="Detalhes do Apartamento">
             <p>Valor: {formatCurrency(selectedApartment.rental_value)}</p>
             <p>Taxa de Limpeza: {formatCurrency(selectedApartment.cleaning_fee)}</p>
             <p>Máximo de Inquilinos: {selectedApartment.max_tenants}</p>
             <p>Móveis: {selectedApartment.furnitures.length} itens</p>
           </Card>
         )}
       </div>
     );
   }
   ```

2. **Lease Creation Wizard - Step 2: Select Responsible Tenant**
   ```typescript
   // Similar to step 1, show tenant dropdown with details
   ```

3. **Lease Creation Wizard - Step 3: Select All Tenants**
   ```typescript
   // app/(dashboard)/leases/_components/wizard-steps/select-tenants.tsx
   import { Select, Alert } from 'antd';

   export function SelectTenantsStep({ value, onChange, responsibleTenantId, maxTenants }) {
     const { data: tenants } = useTenants();

     const handleChange = (selectedIds: number[]) => {
       // Ensure responsible tenant is always included
       if (!selectedIds.includes(responsibleTenantId)) {
         selectedIds.push(responsibleTenantId);
       }
       onChange(selectedIds);
     };

     return (
       <div>
         <Alert
           message={`Máximo de ${maxTenants} inquilinos permitido`}
           type="info"
           className="mb-4"
         />

         <Form.Item
           label="Selecione os Inquilinos"
           rules={[
             { required: true },
             {
               validator: (_, val) => {
                 if (val?.length > maxTenants) {
                   return Promise.reject('Número máximo de inquilinos excedido');
                 }
                 return Promise.resolve();
               },
             },
           ]}
         >
           <Select
             mode="multiple"
             value={value}
             onChange={handleChange}
             options={tenants?.map(t => ({
               value: t.id,
               label: `${t.name} - CPF: ${formatCPF(t.cpf_cnpj)}`,
               disabled: t.id === responsibleTenantId, // Can't deselect responsible
             }))}
           />
         </Form.Item>
       </div>
     );
   }
   ```

4. **Lease Creation Wizard - Step 6: Review with Furniture Calculation**
   ```typescript
   // app/(dashboard)/leases/_components/wizard-steps/review.tsx
   import { Card, Descriptions, List, Tag } from 'antd';
   import { useMemo } from 'react';

   export function ReviewStep({ formData }) {
     const { data: apartment } = useApartment(formData.apartment_id);
     const { data: responsibleTenant } = useTenant(formData.responsible_tenant_id);

     // Calculate furniture included in lease
     const leaseFurniture = useMemo(() => {
       if (!apartment || !responsibleTenant) return [];

       const apartmentFurnitureIds = apartment.furnitures.map(f => f.id);
       const tenantFurnitureIds = responsibleTenant.furnitures.map(f => f.id);

       return apartment.furnitures.filter(
         f => !tenantFurnitureIds.includes(f.id)
       );
     }, [apartment, responsibleTenant]);

     // Calculate tag fee
     const tagFee = formData.tenant_ids?.length === 1 ? 50 : 80;
     const totalValue = formData.rental_value + formData.cleaning_fee + tagFee;

     return (
       <div>
         <Card title="Dados da Locação" className="mb-4">
           <Descriptions>
             <Descriptions.Item label="Apartamento">
               Apto {apartment?.number} - {apartment?.building.name}
             </Descriptions.Item>
             <Descriptions.Item label="Inquilino Responsável">
               {responsibleTenant?.name}
             </Descriptions.Item>
             <Descriptions.Item label="Total de Inquilinos">
               {formData.tenant_ids?.length}
             </Descriptions.Item>
             <Descriptions.Item label="Data Início">
               {formData.start_date}
             </Descriptions.Item>
             <Descriptions.Item label="Validade">
               {formData.validity_months} meses
             </Descriptions.Item>
             <Descriptions.Item label="Dia Vencimento">
               {formData.due_day}
             </Descriptions.Item>
           </Descriptions>
         </Card>

         <Card title="Valores" className="mb-4">
           <Descriptions>
             <Descriptions.Item label="Aluguel">
               {formatCurrency(formData.rental_value)}
             </Descriptions.Item>
             <Descriptions.Item label="Taxa de Limpeza">
               {formatCurrency(formData.cleaning_fee)}
             </Descriptions.Item>
             <Descriptions.Item label="Caução Tag">
               {formatCurrency(tagFee)}
             </Descriptions.Item>
             <Descriptions.Item label="Total">
               <strong>{formatCurrency(totalValue)}</strong>
             </Descriptions.Item>
           </Descriptions>
         </Card>

         <Card title="Móveis Incluídos no Contrato">
           <List
             dataSource={leaseFurniture}
             renderItem={(furniture) => (
               <List.Item>
                 <Tag color="blue">{furniture.name}</Tag>
               </List.Item>
             )}
           />
           {leaseFurniture.length === 0 && (
             <Alert message="Nenhum móvel incluído" type="info" />
           )}
         </Card>
       </div>
     );
   }
   ```

5. **Lease Detail Page with Actions**
   ```typescript
   // app/(dashboard)/leases/[id]/page.tsx
   import { Button, Card, Descriptions, Modal, Tag } from 'antd';
   import { FileTextOutlined, CalculatorOutlined, CalendarOutlined } from '@ant-design/icons';

   export default function LeaseDetailPage({ params }: { params: { id: string } }) {
     const { data: lease } = useLease(params.id);
     const [showLateFeeCalc, setShowLateFeeCalc] = useState(false);
     const [showDueDateChanger, setShowDueDateChanger] = useState(false);

     const handleGenerateContract = async () => {
       try {
         const response = await apiClient.post(
           `/leases/${params.id}/generate_contract/`
         );

         // Download PDF
         const pdfUrl = response.data.pdf_path;
         window.open(pdfUrl, '_blank');

         message.success('Contrato gerado com sucesso!');
       } catch (error) {
         message.error('Erro ao gerar contrato');
       }
     };

     return (
       <div>
         <Card
           title="Detalhes da Locação"
           extra={
             <div className="space-x-2">
               <Button
                 type="primary"
                 icon={<FileTextOutlined />}
                 onClick={handleGenerateContract}
               >
                 Gerar Contrato
               </Button>
               <Button
                 icon={<CalculatorOutlined />}
                 onClick={() => setShowLateFeeCalc(true)}
               >
                 Calcular Multa
               </Button>
               <Button
                 icon={<CalendarOutlined />}
                 onClick={() => setShowDueDateChanger(true)}
               >
                 Alterar Vencimento
               </Button>
             </div>
           }
         >
           {/* Lease details */}
         </Card>

         <LateFeeCalculatorModal
           open={showLateFeeCalc}
           lease={lease}
           onClose={() => setShowLateFeeCalc(false)}
         />

         <DueDateChangerModal
           open={showDueDateChanger}
           lease={lease}
           onClose={() => setShowDueDateChanger(false)}
         />
       </div>
     );
   }
   ```

6. **Late Fee Calculator**
   ```typescript
   // app/(dashboard)/leases/_components/late-fee-calculator-modal.tsx
   import { Modal, Descriptions, Alert } from 'antd';
   import { useQuery } from '@tanstack/react-query';

   export function LateFeeCalculatorModal({ open, lease, onClose }) {
     const { data: feeData } = useQuery({
       queryKey: ['late-fee', lease?.id],
       queryFn: async () => {
         const response = await apiClient.get(
           `/leases/${lease.id}/calculate_late_fee/`
         );
         return response.data;
       },
       enabled: open && !!lease,
     });

     return (
       <Modal
         title="Calculadora de Multa por Atraso"
         open={open}
         onCancel={onClose}
         footer={null}
       >
         {feeData?.late_days ? (
           <div>
             <Alert
               message="Aluguel Atrasado"
               description={`O aluguel está ${feeData.late_days} dias atrasado`}
               type="warning"
               className="mb-4"
             />

             <Descriptions>
               <Descriptions.Item label="Dias de Atraso">
                 {feeData.late_days}
               </Descriptions.Item>
               <Descriptions.Item label="Valor da Multa">
                 <strong>{formatCurrency(feeData.late_fee)}</strong>
               </Descriptions.Item>
               <Descriptions.Item label="Taxa Diária">
                 5% ao dia
               </Descriptions.Item>
             </Descriptions>
           </div>
         ) : (
           <Alert
             message="Aluguel em Dia"
             description="Não há atraso no pagamento"
             type="success"
           />
         )}
       </Modal>
     );
   }
   ```

7. **Due Date Changer**
   ```typescript
   // app/(dashboard)/leases/_components/due-date-changer-modal.tsx
   import { Modal, Form, InputNumber, Alert, Descriptions } from 'antd';
   import { useState, useEffect } from 'react';

   export function DueDateChangerModal({ open, lease, onClose }) {
     const [newDueDay, setNewDueDay] = useState<number>(1);
     const [calculatedFee, setCalculatedFee] = useState<number>(0);
     const changeDueDateMutation = useChangeDueDate();

     useEffect(() => {
       if (lease && newDueDay) {
         // Calculate fee in real-time
         const diffDays = Math.abs(newDueDay - lease.due_day);
         const dailyRate = lease.rental_value / 30;
         setCalculatedFee(dailyRate * diffDays);
       }
     }, [newDueDay, lease]);

     const handleSubmit = async () => {
       try {
         await changeDueDateMutation.mutateAsync({
           id: lease.id,
           new_due_day: newDueDay,
         });
         message.success('Data de vencimento alterada com sucesso!');
         onClose();
       } catch (error) {
         message.error('Erro ao alterar data de vencimento');
       }
     };

     return (
       <Modal
         title="Alterar Data de Vencimento"
         open={open}
         onOk={handleSubmit}
         onCancel={onClose}
         confirmLoading={changeDueDateMutation.isPending}
       >
         <Form layout="vertical">
           <Alert
             message="Atenção"
             description="A alteração do dia de vencimento gerará uma taxa proporcional"
             type="info"
             className="mb-4"
           />

           <Descriptions className="mb-4">
             <Descriptions.Item label="Vencimento Atual">
               Dia {lease?.due_day}
             </Descriptions.Item>
           </Descriptions>

           <Form.Item label="Novo Dia de Vencimento">
             <InputNumber
               min={1}
               max={31}
               value={newDueDay}
               onChange={(val) => setNewDueDay(val || 1)}
             />
           </Form.Item>

           <Descriptions>
             <Descriptions.Item label="Diferença de Dias">
               {Math.abs(newDueDay - (lease?.due_day || 1))} dias
             </Descriptions.Item>
             <Descriptions.Item label="Taxa Proporcional">
               <strong>{formatCurrency(calculatedFee)}</strong>
             </Descriptions.Item>
           </Descriptions>
         </Form>
       </Modal>
     );
   }
   ```

**Deliverables:**
- ✅ Lease creation wizard (6 steps)
- ✅ Validation for apartment availability
- ✅ Tenant count validation
- ✅ Automatic fee calculations
- ✅ Furniture calculation display
- ✅ Contract PDF generation integration
- ✅ Late fee calculator
- ✅ Due date changer
- ✅ 80%+ test coverage

---

### Phase 6: Contract Template Editor (Week 6)

**Goal:** Visual editor for contract template with live preview

**Agents:** `frontend-developer`, `backend-architect`

#### Backend API Endpoints Needed:

```python
# core/views.py - Add these endpoints

@action(detail=False, methods=['get'])
def get_contract_template(self, request):
    """Get current contract template HTML"""
    template_path = os.path.join(settings.BASE_DIR, 'core', 'templates', 'contract_template.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return Response({"content": content}, status=status.HTTP_200_OK)

@action(detail=False, methods=['post'])
def save_contract_template(self, request):
    """Save contract template HTML"""
    content = request.data.get('content')
    if not content:
        return Response({"error": "Content is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Backup current template
    template_path = os.path.join(settings.BASE_DIR, 'core', 'templates', 'contract_template.html')
    backup_path = os.path.join(settings.BASE_DIR, 'core', 'templates', f'contract_template_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html')

    try:
        # Create backup
        shutil.copy(template_path, backup_path)

        # Save new template
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return Response({"message": "Template saved successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@action(detail=False, methods=['post'])
def preview_contract_template(self, request):
    """Render template with sample data"""
    content = request.data.get('content')

    # Get sample lease for preview
    sample_lease = Lease.objects.first()
    if not sample_lease:
        return Response({"error": "No sample lease found"}, status=status.HTTP_404_NOT_FOUND)

    # Render template with sample data
    context = {
        # Same context as generate_contract
        # ...
    }

    from jinja2 import Environment, BaseLoader
    env = Environment(loader=BaseLoader())
    env.filters['currency'] = format_currency
    env.filters['extenso'] = number_to_words

    template = env.from_string(content)
    html_content = template.render(context)

    return Response({"html": html_content}, status=status.HTTP_200_OK)
```

#### Frontend Implementation:

```typescript
// app/(dashboard)/contract-template/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { Card, Button, message, Tabs, Alert } from 'antd';
import { SaveOutlined, EyeOutlined, UndoOutlined } from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export default function ContractTemplatePage() {
  const [content, setContent] = useState('');
  const [previewHtml, setPreviewHtml] = useState('');
  const [activeTab, setActiveTab] = useState('editor');

  const { data: templateData, isLoading } = useQuery({
    queryKey: ['contract-template'],
    queryFn: async () => {
      const response = await apiClient.get('/leases/get_contract_template/');
      return response.data;
    },
  });

  useEffect(() => {
    if (templateData?.content) {
      setContent(templateData.content);
    }
  }, [templateData]);

  const saveMutation = useMutation({
    mutationFn: async (content: string) => {
      const response = await apiClient.post('/leases/save_contract_template/', {
        content,
      });
      return response.data;
    },
    onSuccess: () => {
      message.success('Template salvo com sucesso!');
    },
    onError: () => {
      message.error('Erro ao salvar template');
    },
  });

  const previewMutation = useMutation({
    mutationFn: async (content: string) => {
      const response = await apiClient.post('/leases/preview_contract_template/', {
        content,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setPreviewHtml(data.html);
      setActiveTab('preview');
    },
    onError: () => {
      message.error('Erro ao gerar preview');
    },
  });

  const handleSave = () => {
    saveMutation.mutate(content);
  };

  const handlePreview = () => {
    previewMutation.mutate(content);
  };

  const handleRevert = () => {
    if (templateData?.content) {
      setContent(templateData.content);
      message.info('Alterações revertidas');
    }
  };

  return (
    <div className="h-full">
      <Card
        title="Editor de Template de Contrato"
        extra={
          <div className="space-x-2">
            <Button
              icon={<EyeOutlined />}
              onClick={handlePreview}
              loading={previewMutation.isPending}
            >
              Preview
            </Button>
            <Button
              icon={<UndoOutlined />}
              onClick={handleRevert}
            >
              Reverter
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saveMutation.isPending}
            >
              Salvar
            </Button>
          </div>
        }
      >
        <Alert
          message="Variáveis Disponíveis"
          description={
            <div>
              <p><code>{'{{ tenant.name }}'}</code> - Nome do inquilino</p>
              <p><code>{'{{ building_number }}'}</code> - Número do prédio</p>
              <p><code>{'{{ apartment_number }}'}</code> - Número do apartamento</p>
              <p><code>{'{{ rental_value | currency }}'}</code> - Valor formatado em moeda</p>
              <p><code>{'{{ rental_value | extenso }}'}</code> - Valor por extenso</p>
              <p>E muitas outras... Veja a documentação completa na sidebar.</p>
            </div>
          }
          type="info"
          className="mb-4"
        />

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'editor',
              label: 'Editor',
              children: (
                <div style={{ height: '70vh' }}>
                  <Editor
                    height="100%"
                    defaultLanguage="html"
                    value={content}
                    onChange={(value) => setContent(value || '')}
                    theme="vs-dark"
                    options={{
                      minimap: { enabled: false },
                      fontSize: 14,
                      wordWrap: 'on',
                      formatOnPaste: true,
                      formatOnType: true,
                    }}
                    loading={isLoading ? 'Carregando...' : undefined}
                  />
                </div>
              ),
            },
            {
              key: 'preview',
              label: 'Preview',
              children: (
                <div
                  style={{ height: '70vh', overflow: 'auto' }}
                  className="border rounded p-4 bg-white"
                >
                  {previewHtml ? (
                    <iframe
                      srcDoc={previewHtml}
                      style={{ width: '100%', height: '100%', border: 'none' }}
                      title="Preview"
                    />
                  ) : (
                    <Alert
                      message="Clique em 'Preview' para visualizar o template"
                      type="info"
                    />
                  )}
                </div>
              ),
            },
            {
              key: 'variables',
              label: 'Variáveis',
              children: (
                <div style={{ height: '70vh', overflow: 'auto' }}>
                  <h3>Variáveis de Inquilino</h3>
                  <ul>
                    <li><code>{'{{ tenant.name }}'}</code> - Nome completo</li>
                    <li><code>{'{{ tenant.cpf_cnpj }}'}</code> - CPF ou CNPJ</li>
                    <li><code>{'{{ tenant.rg }}'}</code> - RG</li>
                    <li><code>{'{{ tenant.phone }}'}</code> - Telefone</li>
                    <li><code>{'{{ tenant.marital_status }}'}</code> - Estado civil</li>
                    <li><code>{'{{ tenant.profession }}'}</code> - Profissão</li>
                  </ul>

                  <h3>Variáveis de Apartamento</h3>
                  <ul>
                    <li><code>{'{{ building_number }}'}</code> - Número do prédio</li>
                    <li><code>{'{{ apartment_number }}'}</code> - Número do apartamento</li>
                  </ul>

                  <h3>Variáveis de Locação</h3>
                  <ul>
                    <li><code>{'{{ validity }}'}</code> - Validade em meses</li>
                    <li><code>{'{{ start_date }}'}</code> - Data de início</li>
                    <li><code>{'{{ final_date }}'}</code> - Data final</li>
                    <li><code>{'{{ rental_value }}'}</code> - Valor do aluguel (número)</li>
                    <li><code>{'{{ cleaning_fee }}'}</code> - Taxa de limpeza</li>
                    <li><code>{'{{ valor_tags }}'}</code> - Valor das tags (50 ou 80)</li>
                    <li><code>{'{{ lease.due_day }}'}</code> - Dia de vencimento</li>
                    <li><code>{'{{ lease.number_of_tenants }}'}</code> - Número de inquilinos</li>
                  </ul>

                  <h3>Filtros Jinja2</h3>
                  <ul>
                    <li><code>{'{{ rental_value | currency }}'}</code> - Formata como moeda (R$ 1.500,00)</li>
                    <li><code>{'{{ rental_value | extenso }}'}</code> - Escreve por extenso (mil e quinhentos)</li>
                  </ul>

                  <h3>Loops</h3>
                  <pre>{`{% for furniture in furnitures %}
  <li>{{ furniture.name }}</li>
{% endfor %}`}</pre>

                  <h3>Condicionais</h3>
                  <pre>{`{% if tenant.deposit_amount and tenant.deposit_amount > 0 %}
  <p>Caução: {{ tenant.deposit_amount | currency }}</p>
{% endif %}`}</pre>
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
```

**Deliverables:**
- ✅ Monaco editor integrated
- ✅ Live preview with sample data
- ✅ Save template functionality
- ✅ Revert changes
- ✅ Variables documentation
- ✅ Backend API endpoints
- ✅ Template backup system

---

### Phase 7: Dashboard & Analytics (Week 7)

**Goal:** Comprehensive dashboard with metrics and charts

**Agents:** `frontend-developer`, `data-analyst`

#### Key Features:
- KPI cards (total buildings, apartments, leases, occupancy rate)
- Charts (occupancy, revenue trend, buildings comparison)
- Leases expiring soon widget
- Overdue payments alerts
- Quick actions panel

#### Implementation:

```typescript
// app/(dashboard)/page.tsx
'use client';

import { Row, Col, Card, Statistic, Table, Alert, Button } from 'antd';
import {
  HomeOutlined,
  TeamOutlined,
  FileTextOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { PieChart, Pie, LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export default function DashboardPage() {
  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const [buildings, apartments, leases, tenants] = await Promise.all([
        apiClient.get('/buildings/'),
        apiClient.get('/apartments/'),
        apiClient.get('/leases/'),
        apiClient.get('/tenants/'),
      ]);

      const totalApartments = apartments.data.length;
      const rentedApartments = apartments.data.filter((a: any) => a.is_rented).length;
      const occupancyRate = ((rentedApartments / totalApartments) * 100).toFixed(1);
      const monthlyRevenue = leases.data.reduce(
        (sum: number, l: any) => sum + parseFloat(l.rental_value),
        0
      );

      return {
        totalBuildings: buildings.data.length,
        totalApartments,
        rentedApartments,
        availableApartments: totalApartments - rentedApartments,
        occupancyRate: parseFloat(occupancyRate),
        totalLeases: leases.data.length,
        totalTenants: tenants.data.length,
        monthlyRevenue,
      };
    },
  });

  const occupancyData = [
    { name: 'Alugados', value: stats?.rentedApartments || 0 },
    { name: 'Disponíveis', value: stats?.availableApartments || 0 },
  ];

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

      {/* KPI Cards */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total de Prédios"
              value={stats?.totalBuildings}
              prefix={<HomeOutlined />}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total de Apartamentos"
              value={stats?.totalApartments}
              suffix={`/ ${stats?.rentedApartments} alugados`}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Taxa de Ocupação"
              value={stats?.occupancyRate}
              suffix="%"
              precision={1}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Receita Mensal"
              value={stats?.monthlyRevenue}
              prefix="R$"
              precision={2}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={12}>
          <Card title="Ocupação de Apartamentos">
            <PieChart width={400} height={300}>
              <Pie
                data={occupancyData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                fill="#8884d8"
                label
              />
              <Tooltip />
              <Legend />
            </PieChart>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Locações Expirando em Breve">
            <ExpiringLeasesWidget />
          </Card>
        </Col>
      </Row>

      {/* Quick Actions */}
      <Card title="Ações Rápidas">
        <Row gutter={16}>
          <Col>
            <Button type="primary" href="/dashboard/leases/new">
              Nova Locação
            </Button>
          </Col>
          <Col>
            <Button href="/dashboard/tenants/new">
              Novo Inquilino
            </Button>
          </Col>
          <Col>
            <Button href="/dashboard/apartments/new">
              Novo Apartamento
            </Button>
          </Col>
        </Row>
      </Card>
    </div>
  );
}
```

**Deliverables:**
- ✅ Dashboard with KPI cards
- ✅ Occupancy pie chart
- ✅ Revenue charts
- ✅ Expiring leases widget
- ✅ Quick actions panel
- ✅ Responsive design

---

### Phase 8: Advanced Features & Polish (Week 8)

**Goal:** Global search, advanced filters, bulk operations, export

**Agents:** `frontend-developer`, `ui-ux-designer`

#### Features:
- Global search across all entities
- Advanced filtering system
- Bulk operations (delete, export, status update)
- Excel/CSV export
- Responsive design
- Accessibility improvements

**Deliverables:**
- ✅ Global search working
- ✅ Advanced filters on all pages
- ✅ Bulk operations implemented
- ✅ Export to Excel/CSV
- ✅ Mobile responsive
- ✅ Accessibility audit passed

---

### Phase 9: Testing & Quality Assurance (Week 9)

**Goal:** Comprehensive testing and quality assurance

**Agents:** `test-engineer`, `code-reviewer`

#### Testing Strategy:

1. **Unit Tests** (Vitest + React Testing Library)
   - All components tested (80%+ coverage)
   - All utility functions tested (100%)
   - All custom hooks tested
   - Mock API calls with MSW

2. **Integration Tests**
   - Full user flows tested
   - API integration tests
   - Form submission tests

3. **E2E Tests** (Playwright)
   - Create complete lease workflow
   - Generate contract PDF
   - Edit tenant with dependents
   - Calculate late fees
   - Change due date

4. **Performance Tests**
   - Lighthouse CI (score > 90)
   - Bundle size analysis
   - Render performance

5. **Accessibility Tests**
   - axe-core automated tests
   - Manual screen reader testing
   - Keyboard navigation

**Deliverables:**
- ✅ 80%+ code coverage
- ✅ All E2E tests passing
- ✅ Lighthouse score > 90
- ✅ Accessibility score 100
- ✅ Zero ESLint warnings
- ✅ Zero TypeScript errors

---

### Phase 10: Deployment & DevOps (Week 10)

**Goal:** Production deployment with CI/CD

**Agents:** `devops-engineer`, `nextjs-architecture-expert`

#### Deployment Setup:

1. **Docker Configuration**
   ```dockerfile
   # Dockerfile
   FROM node:20-alpine AS builder

   WORKDIR /app
   COPY package*.json ./
   RUN npm ci
   COPY . .
   RUN npm run build

   FROM node:20-alpine
   WORKDIR /app
   COPY --from=builder /app/.next ./.next
   COPY --from=builder /app/public ./public
   COPY --from=builder /app/package*.json ./
   RUN npm ci --production

   EXPOSE 3000
   CMD ["npm", "start"]
   ```

2. **Docker Compose (Full Stack)**
   ```yaml
   version: '3.8'
   services:
     frontend:
       build: ./frontend
       ports:
         - "3000:3000"
       environment:
         - NEXT_PUBLIC_API_URL=http://backend:8000/api
       depends_on:
         - backend

     backend:
       build: ./
       ports:
         - "8000:8000"
       environment:
         - DATABASE_URL=postgresql://postgres:postgres@db:5432/condominio
       depends_on:
         - db

     db:
       image: postgres:15
       environment:
         - POSTGRES_DB=condominio
         - POSTGRES_USER=postgres
         - POSTGRES_PASSWORD=postgres
       volumes:
         - postgres_data:/var/lib/postgresql/data

   volumes:
     postgres_data:
   ```

3. **CI/CD Pipeline**
   ```yaml
   # .github/workflows/deploy.yml
   name: Deploy to Production

   on:
     push:
       branches: [main]

   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3

         - name: Build and push Docker images
           run: |
             docker-compose build
             docker-compose push

         - name: Deploy to server
           uses: appleboy/ssh-action@master
           with:
             host: ${{ secrets.SERVER_HOST }}
             username: ${{ secrets.SERVER_USER }}
             key: ${{ secrets.SSH_KEY }}
             script: |
               cd /app
               docker-compose pull
               docker-compose up -d
   ```

**Deliverables:**
- ✅ Docker images built
- ✅ CI/CD pipeline configured
- ✅ Production deployment successful
- ✅ Monitoring set up
- ✅ Documentation complete

---

## Agent Orchestration Strategy

### When to Use Which Agent:

1. **Project Setup & Architecture**
   - `nextjs-architecture-expert` - Initial setup, routing decisions
   - `typescript-pro` - Type system design, strict mode configuration

2. **Component Development**
   - `frontend-developer` - UI components, page implementations
   - `ui-ux-designer` - Design system, user experience

3. **Testing**
   - `test-engineer` - Test strategy, test suite implementation
   - `test-automator` - Automated test generation

4. **Code Quality**
   - `code-reviewer` - Review all PRs before merge
   - `solid-dry-enforcer` - Ensure code quality principles

5. **Performance**
   - `react-performance-optimization` - Bundle optimization, lazy loading

6. **Deployment**
   - `devops-engineer` - Docker, CI/CD, infrastructure

---

## Quality Gates Checklist

Every feature must pass these gates before merge:

### Pre-commit (Automated via Husky):
- ✅ ESLint passes (zero warnings)
- ✅ Prettier formatting applied
- ✅ TypeScript compilation succeeds
- ✅ Related unit tests pass

### Pull Request (CI/CD):
- ✅ All unit tests pass
- ✅ Code coverage ≥ 80%
- ✅ Integration tests pass
- ✅ Build succeeds
- ✅ Bundle size within limits

### Pre-merge (Manual):
- ✅ Code review approved
- ✅ E2E tests pass
- ✅ Accessibility audit passed
- ✅ Performance metrics acceptable

### Pre-deployment:
- ✅ All tests passing in staging
- ✅ Security scan passed
- ✅ User acceptance testing completed

---

## Success Metrics

### Technical Metrics:
- Zero ESLint warnings
- Zero TypeScript errors
- 80%+ code coverage
- Lighthouse score > 90
- Bundle size < 500KB (initial load)
- First Contentful Paint < 1.5s
- Time to Interactive < 3s

### Business Metrics:
- All CRUD operations functional
- Contract generation working
- Late fee calculation accurate
- Due date changer working
- Template editor functional
- Dashboard showing real data

---

## Timeline Summary

| Phase | Week | Focus | Deliverable |
|-------|------|-------|-------------|
| 1 | Week 1 | Foundation | Project setup with quality gates |
| 2 | Week 2 | Buildings & Furniture | 2 CRUD modules with tests |
| 3 | Week 3 | Apartments | Complex CRUD with relationships |
| 4 | Week 4 | Tenants | Multi-step wizard with validation |
| 5 | Week 5 | Leases | Complete lease management |
| 6 | Week 6 | Template Editor | Visual contract editor |
| 7 | Week 7 | Dashboard | Analytics and metrics |
| 8 | Week 8 | Advanced Features | Search, filters, bulk ops |
| 9 | Week 9 | Testing & QA | Comprehensive testing |
| 10 | Week 10 | Deployment | Production launch |

**Total Duration:** 10 weeks

---

## Risk Mitigation

### Technical Risks:

1. **PDF Generation Performance**
   - Risk: Pyppeteer is slow
   - Mitigation: Consider WeasyPrint or server-side optimization
   - Fallback: Queue system for contract generation

2. **Large Dataset Performance**
   - Risk: Tables slow with 1000+ records
   - Mitigation: Server-side pagination, virtual scrolling
   - Monitoring: Track performance metrics

3. **TypeScript Strict Mode Challenges**
   - Risk: Slower initial development
   - Mitigation: Use `typescript-pro` agent for complex types
   - Benefit: 80% fewer runtime errors

### Business Risks:

1. **User Training**
   - Mitigation: Comprehensive user manual with screenshots
   - Tooltips and help text throughout UI

2. **Data Migration from Django Admin**
   - Mitigation: Both systems use same database
   - No migration needed

---

## Post-Launch Roadmap

### Phase 11 (Optional - Month 3):
- Real-time notifications (WebSockets)
- Advanced reporting and analytics
- Document management system
- Payment tracking integration
- Email/SMS notifications
- Multi-tenancy support
- Role-based access control

---

## Conclusion

This enterprise-level implementation plan ensures zero-defect delivery through:

1. **Automated Quality Gates** - Pre-commit hooks, CI/CD pipelines
2. **Comprehensive Testing** - Unit, integration, E2E tests with 80%+ coverage
3. **Type Safety** - TypeScript strict mode + Zod runtime validation
4. **Expert Agents** - Specialized agents for each domain
5. **Iterative Development** - 10 phases with clear deliverables
6. **Production Ready** - Docker, CI/CD, monitoring, documentation

**Expected Outcome:** Production-ready, enterprise-grade frontend application with zero errors, zero warnings, and 80%+ test coverage, fully integrated with Django backend, delivered in 10 weeks.
