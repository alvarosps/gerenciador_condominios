# Mobile Setup + Auth — Implementation Plan (Plan 2 of 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the React Native (Expo) mobile project with authentication flows for both admin (email/password) and tenant (CPF + WhatsApp OTP), API client with JWT interceptors, and role-based navigation shell.

**Architecture:** Expo Router file-based routing with `Stack.Protected` guards. Zustand for auth state persisted via `expo-secure-store`. Axios client mirroring the web frontend pattern (interceptors for JWT attach + refresh). Two tab groups: `(tenant)` and `(admin)` rendered conditionally based on user role.

**Tech Stack:** Expo SDK 53, Expo Router 5, React Native, TypeScript (strict), Zustand, Axios, TanStack Query, Zod, expo-secure-store

**Spec:** `docs/superpowers/specs/2026-03-25-mobile-app-design.md` (rev.4)

**Depends on:** Plan 1 (Backend API) — all backend endpoints must be deployed

**Related plans:**
- Plan 1: Backend API (COMPLETE)
- Plan 3: Mobile Tenant Experience (next)
- Plan 4: Mobile Admin Experience
- Plan 5: Push Notifications

---

## File Structure

### New Files (all under `mobile/`)

```
mobile/
├── app.json                          # Expo config (name, slug, scheme, plugins)
├── package.json                      # Dependencies
├── tsconfig.json                     # TypeScript strict config
├── babel.config.js                   # Babel config for Expo
├── .eslintrc.json                    # ESLint config (strict-type-checked)
├── .prettierrc                       # Prettier config
├── app/
│   ├── _layout.tsx                   # Root layout: providers + Stack.Protected auth guard
│   ├── login.tsx                     # Unified login screen (admin tab + tenant tab)
│   ├── (tenant)/
│   │   └── _layout.tsx              # Tenant tab navigator (4 tabs — placeholder screens)
│   └── (admin)/
│       └── _layout.tsx              # Admin tab navigator (5 tabs — placeholder screens)
├── lib/
│   ├── api/
│   │   └── client.ts                # Axios instance + JWT interceptors + token refresh
│   ├── secure-store.ts              # Wrapper around expo-secure-store
│   └── query-client.ts             # TanStack Query client config
├── store/
│   └── auth-store.ts                # Zustand auth store (user, tokens, role)
└── components/
    └── ui/
        └── loading-screen.tsx       # Full-screen loading spinner
```

---

## Task 1: Scaffold Expo Project

**Files:**
- Create: `mobile/` directory with Expo project

- [ ] **Step 1: Create Expo project**

```bash
cd c:/Users/alvar/git/personal/gerenciador_condominios
npx create-expo-app@latest mobile --template blank-typescript
```

Expected: Creates `mobile/` with basic Expo TypeScript project.

- [ ] **Step 2: Install core dependencies**

```bash
cd mobile
npx expo install expo-router expo-secure-store expo-linking expo-constants expo-status-bar react-native-safe-area-context react-native-screens react-native-gesture-handler
npm install axios @tanstack/react-query zustand zod react-native-paper react-native-vector-icons
npm install -D @types/react @typescript-eslint/eslint-plugin @typescript-eslint/parser eslint prettier
```

- [ ] **Step 3: Configure app.json**

Replace `mobile/app.json`:

```json
{
  "expo": {
    "name": "Condominios Manager",
    "slug": "condominios-manager",
    "version": "1.0.0",
    "orientation": "portrait",
    "scheme": "condominios",
    "userInterfaceStyle": "automatic",
    "newArchEnabled": true,
    "ios": {
      "supportsTablet": true,
      "bundleIdentifier": "com.condominios.manager"
    },
    "android": {
      "adaptiveIcon": {
        "backgroundColor": "#ffffff"
      },
      "package": "com.condominios.manager"
    },
    "plugins": [
      "expo-router",
      "expo-secure-store"
    ],
    "experiments": {
      "typedRoutes": true
    }
  }
}
```

- [ ] **Step 4: Configure TypeScript**

Replace `mobile/tsconfig.json`:

```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["**/*.ts", "**/*.tsx", ".expo/types/**/*.ts", "expo-env.d.ts"]
}
```

- [ ] **Step 5: Configure ESLint**

Create `mobile/.eslintrc.json`:

```json
{
  "extends": [
    "expo",
    "plugin:@typescript-eslint/strict-type-checked"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "project": "./tsconfig.json"
  },
  "rules": {
    "@typescript-eslint/consistent-type-imports": ["error", { "prefer": "type-imports", "fixStyle": "inline-type-imports" }],
    "@typescript-eslint/no-explicit-any": "error",
    "no-console": ["warn", { "allow": ["error", "warn"] }],
    "prefer-const": "error",
    "eqeqeq": ["error", "always"]
  }
}
```

- [ ] **Step 6: Create .prettierrc**

Create `mobile/.prettierrc`:

```json
{
  "semi": true,
  "singleQuote": false,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2
}
```

- [ ] **Step 7: Add scripts to package.json**

Ensure `mobile/package.json` has these scripts (merge with existing):

```json
{
  "scripts": {
    "start": "expo start",
    "android": "expo start --android",
    "ios": "expo start --ios",
    "lint": "eslint . --ext .ts,.tsx",
    "type-check": "tsc --noEmit"
  }
}
```

- [ ] **Step 8: Add mobile/.gitignore**

Ensure `mobile/.gitignore` includes:

```
node_modules/
.expo/
dist/
*.jks
*.p8
*.p12
*.key
*.mobileprovision
*.orig.*
web-build/
```

- [ ] **Step 9: Verify project runs**

```bash
cd mobile
npx expo start --clear
```

Expected: Metro bundler starts without errors. Press `a` for Android emulator or scan QR with Expo Go.

- [ ] **Step 10: Commit**

```bash
cd c:/Users/alvar/git/personal/gerenciador_condominios
git add mobile/
git commit -m "feat(mobile): scaffold Expo project with TypeScript and dependencies"
```

---

## Task 2: Secure Store Wrapper

**Files:**
- Create: `mobile/lib/secure-store.ts`

- [ ] **Step 1: Create secure-store wrapper**

Create `mobile/lib/secure-store.ts`:

```typescript
import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

export async function getAccessToken(): Promise<string | null> {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export async function setAccessToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token);
}

export async function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function setRefreshToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token);
}

export async function clearTokens(): Promise<void> {
  await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
}
```

- [ ] **Step 2: Commit**

```bash
git add mobile/lib/secure-store.ts
git commit -m "feat(mobile): add secure-store wrapper for JWT token persistence"
```

---

## Task 3: Zustand Auth Store

**Files:**
- Create: `mobile/store/auth-store.ts`

- [ ] **Step 1: Create auth store**

Create `mobile/store/auth-store.ts`:

```typescript
import { create } from "zustand";

interface User {
  id: number;
  name: string;
  is_staff: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  role: "admin" | "tenant" | null;
}

interface AuthActions {
  setAuth: (user: User, accessToken: string, refreshToken: string) => Promise<void>;
  clearAuth: () => Promise<void>;
  setLoading: (loading: boolean) => void;
  hydrateFromStorage: () => Promise<void>;
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  role: null,

  setAuth: async (user, accessToken, refreshToken) => {
    const { setAccessToken, setRefreshToken } = await import("@/lib/secure-store");
    await setAccessToken(accessToken);
    await setRefreshToken(refreshToken);
    set({
      user,
      isAuthenticated: true,
      isLoading: false,
      role: user.is_staff ? "admin" : "tenant",
    });
  },

  clearAuth: async () => {
    const { clearTokens } = await import("@/lib/secure-store");
    await clearTokens();
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      role: null,
    });
  },

  setLoading: (loading) => set({ isLoading: loading }),

  hydrateFromStorage: async () => {
    const { getAccessToken } = await import("@/lib/secure-store");
    const token = await getAccessToken();
    if (!token) {
      set({ isLoading: false });
      return;
    }
    // Token exists — try to fetch user profile
    try {
      const { apiClient } = await import("@/lib/api/client");
      const response = await apiClient.get<User>("/auth/me/");
      const user = response.data;
      set({
        user,
        isAuthenticated: true,
        isLoading: false,
        role: user.is_staff ? "admin" : "tenant",
      });
    } catch {
      // Token expired or invalid — clear and redirect to login
      const { clearTokens } = await import("@/lib/secure-store");
      await clearTokens();
      set({ isLoading: false });
    }
  },
}));
```

- [ ] **Step 2: Commit**

```bash
git add mobile/store/auth-store.ts
git commit -m "feat(mobile): add Zustand auth store with role detection and hydration"
```

---

## Task 4: API Client with JWT Interceptors

**Files:**
- Create: `mobile/lib/api/client.ts`
- Create: `mobile/lib/query-client.ts`

- [ ] **Step 1: Create API client**

Create `mobile/lib/api/client.ts`:

```typescript
import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor — attach JWT token
apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const { getAccessToken } = await import("@/lib/secure-store");
  const token = await getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — handle 401 with token refresh
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null): void {
  for (const promise of failedQueue) {
    if (token) {
      promise.resolve(token);
    } else {
      promise.reject(error);
    }
  }
  failedQueue = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;
    if (!originalRequest || error.response?.status !== 401) {
      return Promise.reject(error);
    }

    // Avoid infinite loop on refresh endpoint
    if (originalRequest.url?.includes("/auth/token/refresh/")) {
      const { useAuthStore } = await import("@/store/auth-store");
      await useAuthStore.getState().clearAuth();
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return apiClient(originalRequest);
      });
    }

    isRefreshing = true;

    try {
      const { getRefreshToken, setAccessToken } = await import("@/lib/secure-store");
      const refreshToken = await getRefreshToken();
      if (!refreshToken) {
        throw new Error("No refresh token");
      }

      const response = await axios.post<{ access: string }>(
        `${API_BASE_URL}/auth/token/refresh/`,
        { refresh: refreshToken },
      );

      const newAccessToken = response.data.access;
      await setAccessToken(newAccessToken);

      processQueue(null, newAccessToken);

      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      const { useAuthStore } = await import("@/store/auth-store");
      await useAuthStore.getState().clearAuth();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);
```

- [ ] **Step 2: Create TanStack Query client**

Create `mobile/lib/query-client.ts`:

```typescript
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});
```

- [ ] **Step 3: Commit**

```bash
git add mobile/lib/api/client.ts mobile/lib/query-client.ts
git commit -m "feat(mobile): add API client with JWT interceptors and TanStack Query config"
```

---

## Task 5: Root Layout with Auth Guard

**Files:**
- Create: `mobile/app/_layout.tsx`
- Create: `mobile/components/ui/loading-screen.tsx`

- [ ] **Step 1: Create loading screen component**

Create `mobile/components/ui/loading-screen.tsx`:

```typescript
import { ActivityIndicator, StyleSheet, View } from "react-native";

export function LoadingScreen() {
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#2196F3" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
});
```

- [ ] **Step 2: Create root layout**

Create `mobile/app/_layout.tsx`:

```typescript
import { useEffect } from "react";
import { Stack } from "expo-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { PaperProvider } from "react-native-paper";
import { queryClient } from "@/lib/query-client";
import { useAuthStore } from "@/store/auth-store";
import { LoadingScreen } from "@/components/ui/loading-screen";

export default function RootLayout() {
  const { isAuthenticated, isLoading, role, hydrateFromStorage } = useAuthStore();

  useEffect(() => {
    void hydrateFromStorage();
  }, [hydrateFromStorage]);

  if (isLoading) {
    return (
      <PaperProvider>
        <LoadingScreen />
      </PaperProvider>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <PaperProvider>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Protected guard={isAuthenticated && role === "tenant"}>
            <Stack.Screen name="(tenant)" />
          </Stack.Protected>

          <Stack.Protected guard={isAuthenticated && role === "admin"}>
            <Stack.Screen name="(admin)" />
          </Stack.Protected>

          <Stack.Protected guard={!isAuthenticated}>
            <Stack.Screen name="login" />
          </Stack.Protected>
        </Stack>
      </PaperProvider>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add mobile/app/_layout.tsx mobile/components/ui/loading-screen.tsx
git commit -m "feat(mobile): add root layout with auth guard and providers"
```

---

## Task 6: Placeholder Tab Layouts

**Files:**
- Create: `mobile/app/(tenant)/_layout.tsx`
- Create: `mobile/app/(tenant)/index.tsx`
- Create: `mobile/app/(admin)/_layout.tsx`
- Create: `mobile/app/(admin)/index.tsx`

- [ ] **Step 1: Create tenant tab layout**

Create `mobile/app/(tenant)/_layout.tsx`:

```typescript
import { Tabs } from "expo-router";
import FontAwesome from "@expo/vector-icons/FontAwesome";

export default function TenantTabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: "#2196F3",
        tabBarInactiveTintColor: "gray",
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Início",
          tabBarIcon: ({ color }) => <FontAwesome name="home" size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="payments"
        options={{
          title: "Pagamentos",
          tabBarIcon: ({ color }) => <FontAwesome name="credit-card" size={24} color={color} />,
          href: null, // placeholder — will be implemented in Plan 3
        }}
      />
      <Tabs.Screen
        name="contract"
        options={{
          title: "Contrato",
          tabBarIcon: ({ color }) => <FontAwesome name="file-text" size={24} color={color} />,
          href: null,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Perfil",
          tabBarIcon: ({ color }) => <FontAwesome name="user" size={24} color={color} />,
          href: null,
        }}
      />
    </Tabs>
  );
}
```

- [ ] **Step 2: Create tenant home placeholder**

Create `mobile/app/(tenant)/index.tsx`:

```typescript
import { StyleSheet, Text, View } from "react-native";
import { useAuthStore } from "@/store/auth-store";

export default function TenantHome() {
  const { user } = useAuthStore();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Olá, {user?.name ?? "Inquilino"}</Text>
      <Text style={styles.subtitle}>Tela inicial do inquilino</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", alignItems: "center", padding: 16 },
  title: { fontSize: 24, fontWeight: "bold", marginBottom: 8 },
  subtitle: { fontSize: 16, color: "gray" },
});
```

- [ ] **Step 3: Create admin tab layout**

Create `mobile/app/(admin)/_layout.tsx`:

```typescript
import { Tabs } from "expo-router";
import FontAwesome from "@expo/vector-icons/FontAwesome";

export default function AdminTabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: "#2196F3",
        tabBarInactiveTintColor: "gray",
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Dashboard",
          tabBarIcon: ({ color }) => <FontAwesome name="dashboard" size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="properties"
        options={{
          title: "Imóveis",
          tabBarIcon: ({ color }) => <FontAwesome name="building" size={24} color={color} />,
          href: null,
        }}
      />
      <Tabs.Screen
        name="financial"
        options={{
          title: "Financeiro",
          tabBarIcon: ({ color }) => <FontAwesome name="money" size={24} color={color} />,
          href: null,
        }}
      />
      <Tabs.Screen
        name="actions"
        options={{
          title: "Ações",
          tabBarIcon: ({ color }) => <FontAwesome name="bolt" size={24} color={color} />,
          href: null,
        }}
      />
      <Tabs.Screen
        name="notifications"
        options={{
          title: "Alertas",
          tabBarIcon: ({ color }) => <FontAwesome name="bell" size={24} color={color} />,
          href: null,
        }}
      />
    </Tabs>
  );
}
```

- [ ] **Step 4: Create admin home placeholder**

Create `mobile/app/(admin)/index.tsx`:

```typescript
import { StyleSheet, Text, View } from "react-native";
import { useAuthStore } from "@/store/auth-store";

export default function AdminHome() {
  const { user } = useAuthStore();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Dashboard Admin</Text>
      <Text style={styles.subtitle}>Bem-vindo, {user?.name ?? "Admin"}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", alignItems: "center", padding: 16 },
  title: { fontSize: 24, fontWeight: "bold", marginBottom: 8 },
  subtitle: { fontSize: 16, color: "gray" },
});
```

- [ ] **Step 5: Commit**

```bash
git add mobile/app/(tenant)/ mobile/app/(admin)/
git commit -m "feat(mobile): add placeholder tab layouts for tenant and admin"
```

---

## Task 7: Login Screen

**Files:**
- Create: `mobile/app/login.tsx`

- [ ] **Step 1: Create unified login screen**

Create `mobile/app/login.tsx`:

```typescript
import { useState } from "react";
import { Alert, Keyboard, KeyboardAvoidingView, Platform, StyleSheet, View } from "react-native";
import { Button, SegmentedButtons, Text, TextInput } from "react-native-paper";
import { apiClient } from "@/lib/api/client";
import { useAuthStore } from "@/store/auth-store";

type LoginMode = "admin" | "tenant";

interface AdminLoginData {
  username: string;
  password: string;
}

interface TenantRequestData {
  cpf_cnpj: string;
}

interface TenantVerifyData {
  cpf_cnpj: string;
  code: string;
}

interface TokenResponse {
  access: string;
  refresh: string;
}

interface UserResponse {
  id: number;
  first_name: string;
  last_name: string;
  is_staff: boolean;
}

export default function LoginScreen() {
  const { setAuth } = useAuthStore();
  const [mode, setMode] = useState<LoginMode>("tenant");

  // Admin state
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // Tenant state
  const [cpfCnpj, setCpfCnpj] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);

  const [loading, setLoading] = useState(false);

  async function handleAdminLogin(): Promise<void> {
    if (!username || !password) {
      Alert.alert("Erro", "Preencha todos os campos.");
      return;
    }
    setLoading(true);
    try {
      const tokenRes = await apiClient.post<TokenResponse>("/auth/token/", {
        username,
        password,
      });
      const userRes = await apiClient.get<UserResponse>("/auth/me/", {
        headers: { Authorization: `Bearer ${tokenRes.data.access}` },
      });
      const user = {
        id: userRes.data.id,
        name: `${userRes.data.first_name} ${userRes.data.last_name}`.trim(),
        is_staff: userRes.data.is_staff,
      };
      await setAuth(user, tokenRes.data.access, tokenRes.data.refresh);
    } catch {
      Alert.alert("Erro", "Credenciais inválidas.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRequestCode(): Promise<void> {
    if (!cpfCnpj) {
      Alert.alert("Erro", "Digite seu CPF ou CNPJ.");
      return;
    }
    setLoading(true);
    try {
      await apiClient.post("/auth/whatsapp/request/", { cpf_cnpj: cpfCnpj });
      setCodeSent(true);
      Alert.alert("Código enviado", "Verifique seu WhatsApp.");
    } catch {
      Alert.alert("Erro", "CPF/CNPJ não encontrado ou muitas tentativas.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyCode(): Promise<void> {
    if (!code) {
      Alert.alert("Erro", "Digite o código de verificação.");
      return;
    }
    setLoading(true);
    try {
      const res = await apiClient.post<TokenResponse>("/auth/whatsapp/verify/", {
        cpf_cnpj: cpfCnpj,
        code,
      });
      // Fetch tenant profile to get name
      const meRes = await apiClient.get<{
        id: number;
        name: string;
      }>("/tenant/me/", {
        headers: { Authorization: `Bearer ${res.data.access}` },
      });
      const user = {
        id: meRes.data.id,
        name: meRes.data.name,
        is_staff: false,
      };
      await setAuth(user, res.data.access, res.data.refresh);
    } catch {
      Alert.alert("Erro", "Código inválido ou expirado.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.inner}>
        <Text variant="headlineMedium" style={styles.title}>
          Condominios Manager
        </Text>

        <SegmentedButtons
          value={mode}
          onValueChange={(v) => {
            setMode(v as LoginMode);
            setCodeSent(false);
          }}
          buttons={[
            { value: "tenant", label: "Inquilino" },
            { value: "admin", label: "Administrador" },
          ]}
          style={styles.segmented}
        />

        {mode === "admin" ? (
          <View style={styles.form}>
            <TextInput
              label="Usuário"
              value={username}
              onChangeText={setUsername}
              autoCapitalize="none"
              mode="outlined"
              style={styles.input}
            />
            <TextInput
              label="Senha"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              mode="outlined"
              style={styles.input}
            />
            <Button
              mode="contained"
              onPress={() => void handleAdminLogin()}
              loading={loading}
              disabled={loading}
              style={styles.button}
            >
              Entrar
            </Button>
          </View>
        ) : (
          <View style={styles.form}>
            <TextInput
              label="CPF ou CNPJ"
              value={cpfCnpj}
              onChangeText={setCpfCnpj}
              keyboardType="numeric"
              mode="outlined"
              style={styles.input}
              disabled={codeSent}
            />
            {codeSent ? (
              <>
                <TextInput
                  label="Código de verificação"
                  value={code}
                  onChangeText={setCode}
                  keyboardType="numeric"
                  maxLength={6}
                  mode="outlined"
                  style={styles.input}
                />
                <Button
                  mode="contained"
                  onPress={() => void handleVerifyCode()}
                  loading={loading}
                  disabled={loading}
                  style={styles.button}
                >
                  Verificar
                </Button>
                <Button
                  mode="text"
                  onPress={() => {
                    setCodeSent(false);
                    setCode("");
                  }}
                  style={styles.button}
                >
                  Reenviar código
                </Button>
              </>
            ) : (
              <Button
                mode="contained"
                onPress={() => void handleRequestCode()}
                loading={loading}
                disabled={loading}
                style={styles.button}
              >
                Enviar código via WhatsApp
              </Button>
            )}
          </View>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  inner: { flex: 1, justifyContent: "center", padding: 24 },
  title: { textAlign: "center", marginBottom: 32 },
  segmented: { marginBottom: 24 },
  form: { gap: 12 },
  input: { marginBottom: 4 },
  button: { marginTop: 8 },
});
```

- [ ] **Step 2: Verify login screen renders**

```bash
cd mobile
npx expo start --clear
```

Expected: App loads → shows login screen with "Inquilino" / "Administrador" toggle.

- [ ] **Step 3: Commit**

```bash
git add mobile/app/login.tsx
git commit -m "feat(mobile): add unified login screen with admin and tenant auth flows"
```

---

## Task 8: Environment Configuration

**Files:**
- Create: `mobile/.env`
- Create: `mobile/.env.example`

- [ ] **Step 1: Create .env files**

Create `mobile/.env.example`:

```
EXPO_PUBLIC_API_URL=http://localhost:8000/api
```

Create `mobile/.env` (gitignored):

```
EXPO_PUBLIC_API_URL=http://localhost:8000/api
```

- [ ] **Step 2: Add .env to .gitignore**

Append to `mobile/.gitignore`:

```
.env
.env.local
```

- [ ] **Step 3: Commit**

```bash
git add mobile/.env.example mobile/.gitignore
git commit -m "chore(mobile): add environment configuration"
```

---

## Self-Review Checklist

### Spec Coverage
- [x] Expo project scaffold with TypeScript — Task 1
- [x] expo-secure-store wrapper — Task 2
- [x] Zustand auth store with role detection — Task 3
- [x] Axios client with JWT interceptors + token refresh — Task 4
- [x] Root layout with Stack.Protected auth guard — Task 5
- [x] Tenant tab layout (4 tabs) — Task 6
- [x] Admin tab layout (5 tabs) — Task 6
- [x] Login screen — admin (email/password) — Task 7
- [x] Login screen — tenant (CPF + WhatsApp OTP) — Task 7
- [x] Token refresh on app resume — Task 3 (hydrateFromStorage)
- [x] Environment config — Task 8
- [x] TanStack Query client — Task 4

### Not in this plan (deferred to Plans 3-5)
- Tenant screens (home, payments, PIX, contract, profile) — Plan 3
- Admin screens (dashboard, properties, financial, actions, notifications) — Plan 4
- Push notifications (expo-notifications, deep linking) — Plan 5
- react-native-qrcode-svg (PIX QR code rendering) — Plan 3
- expo-image-picker / expo-document-picker (proof upload) — Plan 3
