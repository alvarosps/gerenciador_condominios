# Mobile Tenant Experience — Implementation Plan (Plan 3 of 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all 4 tenant tab screens — Home (resumo + alertas), Pagamentos (PIX, comprovante, histórico, simulação, reajustes), Contrato (PDF + dados imóvel), Perfil (dados + dependentes + logout).

**Architecture:** Expo Router file-based routing under `app/(tenant)/`. TanStack Query hooks for API communication. Each screen is a standalone file consuming the existing API client and auth store from Plan 2.

**Tech Stack:** Expo Router, React Native Paper, TanStack Query, Zod, expo-image-picker, expo-document-picker, react-native-qrcode-svg, expo-file-system, expo-sharing

**Spec:** `docs/superpowers/specs/2026-03-25-mobile-app-design.md` — Seções: Inquilino Tab Bar, Regras de Negócio Tenant Inativo, Lógica PIX

**Depends on:** Plan 1 (Backend API), Plan 2 (Mobile Setup + Auth)

---

## File Structure

```
mobile/
├── app/(tenant)/
│   ├── _layout.tsx              # UPDATE — add all 4 tabs
│   ├── index.tsx                # UPDATE — full home screen with summary + alerts
│   ├── payments/
│   │   ├── _layout.tsx          # Stack navigator for payments
│   │   ├── index.tsx            # Payment history list + quick pay button
│   │   ├── pix.tsx              # PIX generation + QR code + proof upload
│   │   ├── simulate.tsx         # Due date change simulation
│   │   └── adjustments.tsx      # Rent adjustment history
│   ├── contract.tsx             # Contract PDF viewer + property data
│   └── profile.tsx              # Profile data + dependents + logout
├── lib/api/hooks/
│   ├── use-tenant.ts            # Hooks: useTenantMe, useTenantPayments, useTenantAdjustments
│   ├── use-tenant-pix.ts        # Hooks: useGeneratePix
│   ├── use-tenant-proof.ts      # Hooks: useUploadProof, useProofStatus
│   ├── use-tenant-simulate.ts   # Hooks: useSimulateDueDate
│   └── use-tenant-notifications.ts # Hooks: useTenantNotifications, useMarkRead, useMarkAllRead
└── lib/schemas/
    └── tenant.ts                # Zod schemas for tenant API responses
```

---

## Task 1: Install Additional Dependencies

**Files:** none (shell commands only)

- [ ] **Step 1: Install image/doc picker and QR code**

```bash
cd mobile
npx expo install expo-image-picker expo-document-picker expo-file-system expo-sharing
npm install --legacy-peer-deps react-native-qrcode-svg react-native-svg
```

- [ ] **Step 2: Commit**

```bash
git add mobile/package.json mobile/package-lock.json
git commit -m "chore(mobile): add image picker, document picker, QR code dependencies"
```

---

## Task 2: Tenant API Hooks

**Files:**
- Create: `mobile/lib/api/hooks/use-tenant.ts`
- Create: `mobile/lib/api/hooks/use-tenant-pix.ts`
- Create: `mobile/lib/api/hooks/use-tenant-proof.ts`
- Create: `mobile/lib/api/hooks/use-tenant-simulate.ts`
- Create: `mobile/lib/api/hooks/use-tenant-notifications.ts`
- Create: `mobile/lib/schemas/tenant.ts`

- [ ] **Step 1: Create Zod schemas**

Create `mobile/lib/schemas/tenant.ts`:

```typescript
import { z } from "zod";

export const tenantMeSchema = z.object({
  id: z.number(),
  name: z.string(),
  cpf_cnpj: z.string(),
  is_company: z.boolean(),
  rg: z.string().nullable(),
  phone: z.string(),
  marital_status: z.string(),
  profession: z.string(),
  due_day: z.number(),
  warning_count: z.number(),
  dependents: z.array(
    z.object({
      id: z.number(),
      name: z.string(),
      phone: z.string().nullable(),
      cpf_cnpj: z.string().nullable(),
    }),
  ),
  lease: z
    .object({
      id: z.number(),
      start_date: z.string(),
      validity_months: z.number(),
      rental_value: z.string(),
      pending_rental_value: z.string().nullable(),
      pending_rental_value_date: z.string().nullable(),
      number_of_tenants: z.number(),
      contract_generated: z.boolean(),
    })
    .nullable()
    .optional(),
  apartment: z
    .object({
      id: z.number(),
      number: z.number(),
      building_name: z.string(),
      building_address: z.string(),
    })
    .nullable()
    .optional(),
});

export type TenantMe = z.infer<typeof tenantMeSchema>;

export const rentPaymentSchema = z.object({
  id: z.number(),
  lease: z.number(),
  reference_month: z.string(),
  amount_paid: z.string(),
  payment_date: z.string(),
  notes: z.string().nullable(),
});

export type RentPayment = z.infer<typeof rentPaymentSchema>;

export const rentAdjustmentSchema = z.object({
  id: z.number(),
  lease: z.number(),
  adjustment_date: z.string(),
  percentage: z.string(),
  previous_value: z.string(),
  new_value: z.string(),
  apartment_updated: z.boolean(),
});

export type RentAdjustment = z.infer<typeof rentAdjustmentSchema>;

export const pixPayloadSchema = z.object({
  pix_copy_paste: z.string(),
  qr_data: z.string(),
  pix_key: z.string(),
  pix_key_type: z.string(),
  amount: z.string(),
  merchant_name: z.string(),
});

export type PixPayload = z.infer<typeof pixPayloadSchema>;

export const paymentProofSchema = z.object({
  id: z.number(),
  reference_month: z.string(),
  file: z.string(),
  pix_code: z.string(),
  status: z.enum(["pending", "approved", "rejected"]),
  rejection_reason: z.string().nullable(),
  created_at: z.string(),
});

export type PaymentProof = z.infer<typeof paymentProofSchema>;

export const simulateDueDateSchema = z.object({
  current_due_day: z.number(),
  new_due_day: z.number(),
  days_difference: z.number(),
  daily_rate: z.string(),
  fee: z.string(),
});

export type SimulateDueDate = z.infer<typeof simulateDueDateSchema>;

export const notificationSchema = z.object({
  id: z.number(),
  type: z.string(),
  title: z.string(),
  body: z.string(),
  is_read: z.boolean(),
  read_at: z.string().nullable(),
  sent_at: z.string(),
  data: z.record(z.unknown()).nullable(),
});

export type TenantNotification = z.infer<typeof notificationSchema>;
```

- [ ] **Step 2: Create tenant data hooks**

Create `mobile/lib/api/hooks/use-tenant.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { TenantMe, RentPayment, RentAdjustment } from "@/lib/schemas/tenant";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export function useTenantMe() {
  return useQuery({
    queryKey: ["tenant", "me"],
    queryFn: async () => {
      const res = await apiClient.get<TenantMe>("/tenant/me/");
      return res.data;
    },
  });
}

export function useTenantPayments() {
  return useQuery({
    queryKey: ["tenant", "payments"],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<RentPayment>>("/tenant/payments/");
      return res.data.results;
    },
  });
}

export function useTenantAdjustments() {
  return useQuery({
    queryKey: ["tenant", "rent-adjustments"],
    queryFn: async () => {
      const res = await apiClient.get<{ results: RentAdjustment[] }>("/tenant/rent-adjustments/");
      return res.data.results;
    },
  });
}
```

- [ ] **Step 3: Create PIX hook**

Create `mobile/lib/api/hooks/use-tenant-pix.ts`:

```typescript
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { PixPayload } from "@/lib/schemas/tenant";

export function useGeneratePix() {
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post<PixPayload>("/tenant/payments/pix/");
      return res.data;
    },
  });
}
```

- [ ] **Step 4: Create proof upload hook**

Create `mobile/lib/api/hooks/use-tenant-proof.ts`:

```typescript
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { PaymentProof } from "@/lib/schemas/tenant";

export function useUploadProof() {
  return useMutation({
    mutationFn: async (data: { referenceMonth: string; file: { uri: string; name: string; type: string }; pixCode?: string }) => {
      const formData = new FormData();
      formData.append("reference_month", data.referenceMonth);
      formData.append("file", {
        uri: data.file.uri,
        name: data.file.name,
        type: data.file.type,
      } as unknown as Blob);
      if (data.pixCode) {
        formData.append("pix_code", data.pixCode);
      }
      const res = await apiClient.post<PaymentProof>("/tenant/payments/proof/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
  });
}

export function useProofStatus(proofId: number | null) {
  return useQuery({
    queryKey: ["tenant", "proof", proofId],
    queryFn: async () => {
      const res = await apiClient.get<PaymentProof>(`/tenant/payments/proof/${proofId}/`);
      return res.data;
    },
    enabled: proofId !== null,
  });
}
```

- [ ] **Step 5: Create simulate hook**

Create `mobile/lib/api/hooks/use-tenant-simulate.ts`:

```typescript
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { SimulateDueDate } from "@/lib/schemas/tenant";

export function useSimulateDueDate() {
  return useMutation({
    mutationFn: async (newDueDay: number) => {
      const res = await apiClient.post<SimulateDueDate>("/tenant/due-date/simulate/", {
        new_due_day: newDueDay,
      });
      return res.data;
    },
  });
}
```

- [ ] **Step 6: Create notifications hook**

Create `mobile/lib/api/hooks/use-tenant-notifications.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { TenantNotification } from "@/lib/schemas/tenant";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export function useTenantNotifications() {
  return useQuery({
    queryKey: ["tenant", "notifications"],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<TenantNotification>>("/tenant/notifications/");
      return res.data.results;
    },
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: number) => {
      await apiClient.patch(`/tenant/notifications/${notificationId}/read/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tenant", "notifications"] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await apiClient.post<{ marked_read: number }>("/tenant/notifications/read-all/");
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tenant", "notifications"] });
    },
  });
}
```

- [ ] **Step 7: Commit**

```bash
git add mobile/lib/
git commit -m "feat(mobile): add tenant API hooks and Zod schemas"
```

---

## Task 3: Update Tenant Tab Layout (4 tabs)

**Files:**
- Modify: `mobile/app/(tenant)/_layout.tsx`
- Create: `mobile/app/(tenant)/payments/_layout.tsx`

- [ ] **Step 1: Update tenant tab layout with all 4 tabs**

Replace `mobile/app/(tenant)/_layout.tsx`:

```typescript
import { Tabs } from "expo-router";
import FontAwesome from "@expo/vector-icons/FontAwesome";

export default function TenantTabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: "#2196F3",
        tabBarInactiveTintColor: "gray",
        headerShown: true,
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
          headerShown: false,
          tabBarIcon: ({ color }) => <FontAwesome name="credit-card" size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="contract"
        options={{
          title: "Contrato",
          tabBarIcon: ({ color }) => <FontAwesome name="file-text" size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Perfil",
          tabBarIcon: ({ color }) => <FontAwesome name="user" size={24} color={color} />,
        }}
      />
    </Tabs>
  );
}
```

- [ ] **Step 2: Create payments stack layout**

Create `mobile/app/(tenant)/payments/_layout.tsx`:

```typescript
import { Stack } from "expo-router";

export default function PaymentsLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: "Pagamentos" }} />
      <Stack.Screen name="pix" options={{ title: "Pagar Aluguel" }} />
      <Stack.Screen name="simulate" options={{ title: "Simular Vencimento" }} />
      <Stack.Screen name="adjustments" options={{ title: "Reajustes" }} />
    </Stack>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add mobile/app/(tenant)/
git commit -m "feat(mobile): update tenant tabs — 4 tabs with payments stack navigator"
```

---

## Task 4: Tenant Home Screen

**Files:**
- Modify: `mobile/app/(tenant)/index.tsx`

- [ ] **Step 1: Implement home screen with summary and alerts**

Replace `mobile/app/(tenant)/index.tsx`:

```typescript
import { ScrollView, StyleSheet, View } from "react-native";
import { Button, Card, Text, ActivityIndicator, Chip } from "react-native-paper";
import { useRouter } from "expo-router";
import { useTenantMe } from "@/lib/api/hooks/use-tenant";
import { useTenantNotifications } from "@/lib/api/hooks/use-tenant-notifications";

export default function TenantHome() {
  const router = useRouter();
  const { data: me, isLoading } = useTenantMe();
  const { data: notifications } = useTenantNotifications();

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  const lease = me?.lease;
  const apartment = me?.apartment;
  const unreadNotifs = notifications?.filter((n) => !n.is_read) ?? [];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text variant="headlineSmall" style={styles.greeting}>
        Olá, {me?.name ?? "Inquilino"}
      </Text>

      {!lease ? (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="titleMedium">Sem locação ativa</Text>
            <Text variant="bodyMedium" style={styles.muted}>
              Seu contrato foi encerrado.
            </Text>
          </Card.Content>
        </Card>
      ) : (
        <>
          {/* Resumo do aluguel */}
          <Card style={styles.card}>
            <Card.Content>
              <Text variant="titleMedium">Próximo Vencimento</Text>
              <Text variant="headlineMedium" style={styles.amount}>
                R$ {lease.rental_value}
              </Text>
              <Text variant="bodyMedium" style={styles.muted}>
                Vencimento dia {me?.due_day} · Apto {apartment?.number} · {apartment?.building_name}
              </Text>
            </Card.Content>
            <Card.Actions>
              <Button mode="contained" onPress={() => router.push("/(tenant)/payments/pix")}>
                Pagar
              </Button>
            </Card.Actions>
          </Card>

          {/* Alerta de reajuste pendente */}
          {lease.pending_rental_value && (
            <Card style={[styles.card, styles.alertCard]}>
              <Card.Content>
                <Text variant="titleMedium">Reajuste Pendente</Text>
                <Text variant="bodyMedium">
                  Seu aluguel será reajustado para R$ {lease.pending_rental_value} a partir de{" "}
                  {lease.pending_rental_value_date ?? "data a definir"}.
                </Text>
              </Card.Content>
            </Card>
          )}
        </>
      )}

      {/* Notificações não lidas */}
      {unreadNotifs.length > 0 && (
        <Card style={styles.card}>
          <Card.Content>
            <View style={styles.row}>
              <Text variant="titleMedium">Avisos</Text>
              <Chip compact>{unreadNotifs.length}</Chip>
            </View>
            {unreadNotifs.slice(0, 3).map((n) => (
              <View key={n.id} style={styles.notifItem}>
                <Text variant="bodyMedium" style={styles.bold}>
                  {n.title}
                </Text>
                <Text variant="bodySmall" style={styles.muted}>
                  {n.body}
                </Text>
              </View>
            ))}
          </Card.Content>
        </Card>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 16, gap: 16 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center" },
  greeting: { marginBottom: 8 },
  card: { borderRadius: 12 },
  alertCard: { backgroundColor: "#FFF3E0" },
  amount: { marginVertical: 8 },
  muted: { color: "gray" },
  bold: { fontWeight: "bold" },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  notifItem: { marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: "#eee" },
});
```

- [ ] **Step 2: Commit**

```bash
git add mobile/app/(tenant)/index.tsx
git commit -m "feat(mobile): implement tenant home screen with summary, alerts, and quick pay"
```

---

## Task 5: Payments List Screen

**Files:**
- Create: `mobile/app/(tenant)/payments/index.tsx`

- [ ] **Step 1: Implement payments history list**

Create `mobile/app/(tenant)/payments/index.tsx`:

```typescript
import { FlatList, StyleSheet, View } from "react-native";
import { ActivityIndicator, Button, Card, Text } from "react-native-paper";
import { useRouter } from "expo-router";
import { useTenantPayments } from "@/lib/api/hooks/use-tenant";

export default function PaymentsList() {
  const router = useRouter();
  const { data: payments, isLoading } = useTenantPayments();

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.actions}>
        <Button mode="contained" onPress={() => router.push("/(tenant)/payments/pix")} icon="cash">
          Pagar Aluguel
        </Button>
        <View style={styles.row}>
          <Button mode="outlined" onPress={() => router.push("/(tenant)/payments/simulate")} compact>
            Simular Vencimento
          </Button>
          <Button mode="outlined" onPress={() => router.push("/(tenant)/payments/adjustments")} compact>
            Reajustes
          </Button>
        </View>
      </View>

      <Text variant="titleMedium" style={styles.sectionTitle}>
        Histórico de Pagamentos
      </Text>

      <FlatList
        data={payments}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <Card style={styles.paymentCard}>
            <Card.Content style={styles.paymentRow}>
              <View>
                <Text variant="bodyMedium" style={styles.bold}>
                  {new Date(item.reference_month).toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}
                </Text>
                <Text variant="bodySmall" style={styles.muted}>
                  Pago em {new Date(item.payment_date).toLocaleDateString("pt-BR")}
                </Text>
              </View>
              <Text variant="titleMedium" style={styles.amount}>
                R$ {item.amount_paid}
              </Text>
            </Card.Content>
          </Card>
        )}
        ListEmptyComponent={
          <Text variant="bodyMedium" style={styles.empty}>
            Nenhum pagamento registrado.
          </Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center" },
  actions: { gap: 12, marginBottom: 16 },
  row: { flexDirection: "row", gap: 8 },
  sectionTitle: { marginBottom: 12 },
  paymentCard: { marginBottom: 8, borderRadius: 8 },
  paymentRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  bold: { fontWeight: "bold" },
  muted: { color: "gray" },
  amount: { color: "#2E7D32" },
  empty: { textAlign: "center", color: "gray", marginTop: 32 },
});
```

- [ ] **Step 2: Commit**

```bash
git add mobile/app/(tenant)/payments/index.tsx
git commit -m "feat(mobile): add tenant payments list with history and action buttons"
```

---

## Task 6: PIX Payment + Proof Upload Screen

**Files:**
- Create: `mobile/app/(tenant)/payments/pix.tsx`

- [ ] **Step 1: Implement PIX screen with QR code and proof upload**

Create `mobile/app/(tenant)/payments/pix.tsx`:

```typescript
import { useState } from "react";
import { Alert, ScrollView, StyleSheet, View } from "react-native";
import { ActivityIndicator, Button, Card, Text, TextInput } from "react-native-paper";
import * as Clipboard from "expo-clipboard";
import * as ImagePicker from "expo-image-picker";
import * as DocumentPicker from "expo-document-picker";
import QRCode from "react-native-qrcode-svg";
import { useRouter } from "expo-router";
import { useTenantMe } from "@/lib/api/hooks/use-tenant";
import { useGeneratePix } from "@/lib/api/hooks/use-tenant-pix";
import { useUploadProof } from "@/lib/api/hooks/use-tenant-proof";

export default function PixPaymentScreen() {
  const router = useRouter();
  const { data: me } = useTenantMe();
  const generatePix = useGeneratePix();
  const uploadProof = useUploadProof();
  const [pixData, setPixData] = useState<{ pix_copy_paste: string; qr_data: string; amount: string } | null>(null);
  const [referenceMonth, setReferenceMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  });

  async function handleGeneratePix(): Promise<void> {
    try {
      const result = await generatePix.mutateAsync();
      setPixData(result);
    } catch {
      Alert.alert("Erro", "Não foi possível gerar o PIX. Chave PIX pode não estar cadastrada.");
    }
  }

  async function handleCopyPix(): Promise<void> {
    if (pixData) {
      await Clipboard.setStringAsync(pixData.pix_copy_paste);
      Alert.alert("Copiado", "Código PIX copiado para a área de transferência.");
    }
  }

  async function handlePickImage(): Promise<void> {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.8,
    });
    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      await submitProof({
        uri: asset.uri,
        name: asset.fileName ?? "comprovante.jpg",
        type: asset.mimeType ?? "image/jpeg",
      });
    }
  }

  async function handlePickDocument(): Promise<void> {
    const result = await DocumentPicker.getDocumentAsync({ type: "application/pdf" });
    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      await submitProof({
        uri: asset.uri,
        name: asset.name,
        type: asset.mimeType ?? "application/pdf",
      });
    }
  }

  async function submitProof(file: { uri: string; name: string; type: string }): Promise<void> {
    try {
      await uploadProof.mutateAsync({
        referenceMonth,
        file,
        pixCode: pixData?.pix_copy_paste,
      });
      Alert.alert("Sucesso", "Comprovante enviado. Aguarde a aprovação do administrador.", [
        { text: "OK", onPress: () => router.back() },
      ]);
    } catch {
      Alert.alert("Erro", "Falha ao enviar comprovante.");
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium">Valor do Aluguel</Text>
          <Text variant="headlineMedium" style={styles.amount}>
            R$ {me?.lease?.rental_value ?? "—"}
          </Text>
          <Text variant="bodySmall" style={styles.muted}>
            Apto {me?.apartment?.number} · {me?.apartment?.building_name}
          </Text>
        </Card.Content>
      </Card>

      {!pixData ? (
        <Button
          mode="contained"
          onPress={() => void handleGeneratePix()}
          loading={generatePix.isPending}
          disabled={generatePix.isPending}
          icon="qrcode"
          style={styles.button}
        >
          Gerar PIX
        </Button>
      ) : (
        <>
          <Card style={styles.card}>
            <Card.Content style={styles.qrContainer}>
              <QRCode value={pixData.qr_data} size={200} />
              <Text variant="bodySmall" style={[styles.muted, styles.qrHint]}>
                Escaneie o QR Code ou copie o código abaixo
              </Text>
              <Button mode="outlined" onPress={() => void handleCopyPix()} icon="content-copy">
                Copiar código PIX
              </Button>
            </Card.Content>
          </Card>

          <Card style={styles.card}>
            <Card.Content>
              <Text variant="titleMedium" style={styles.proofTitle}>
                Enviar Comprovante
              </Text>
              <Text variant="bodySmall" style={styles.muted}>
                Após efetuar o pagamento, envie o comprovante.
              </Text>
              <TextInput
                label="Mês de referência"
                value={referenceMonth}
                onChangeText={setReferenceMonth}
                mode="outlined"
                style={styles.input}
              />
              <View style={styles.proofButtons}>
                <Button
                  mode="outlined"
                  onPress={() => void handlePickImage()}
                  icon="camera"
                  loading={uploadProof.isPending}
                >
                  Foto
                </Button>
                <Button
                  mode="outlined"
                  onPress={() => void handlePickDocument()}
                  icon="file-pdf-box"
                  loading={uploadProof.isPending}
                >
                  PDF
                </Button>
              </View>
            </Card.Content>
          </Card>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 16, gap: 16 },
  card: { borderRadius: 12 },
  amount: { marginVertical: 8 },
  muted: { color: "gray" },
  button: { marginTop: 8 },
  qrContainer: { alignItems: "center", gap: 16 },
  qrHint: { marginTop: 8 },
  proofTitle: { marginBottom: 8 },
  input: { marginVertical: 8 },
  proofButtons: { flexDirection: "row", gap: 12, marginTop: 8 },
});
```

- [ ] **Step 2: Commit**

```bash
git add mobile/app/(tenant)/payments/pix.tsx
git commit -m "feat(mobile): add PIX payment screen with QR code and proof upload"
```

---

## Task 7: Simulate Due Date + Adjustments Screens

**Files:**
- Create: `mobile/app/(tenant)/payments/simulate.tsx`
- Create: `mobile/app/(tenant)/payments/adjustments.tsx`

- [ ] **Step 1: Implement due date simulation screen**

Create `mobile/app/(tenant)/payments/simulate.tsx`:

```typescript
import { useState } from "react";
import { Alert, StyleSheet, View } from "react-native";
import { Button, Card, Text, TextInput } from "react-native-paper";
import { useSimulateDueDate } from "@/lib/api/hooks/use-tenant-simulate";
import { useTenantMe } from "@/lib/api/hooks/use-tenant";

export default function SimulateDueDateScreen() {
  const { data: me } = useTenantMe();
  const simulate = useSimulateDueDate();
  const [newDueDay, setNewDueDay] = useState("");

  async function handleSimulate(): Promise<void> {
    const day = parseInt(newDueDay, 10);
    if (isNaN(day) || day < 1 || day > 31) {
      Alert.alert("Erro", "Digite um dia válido (1-31).");
      return;
    }
    try {
      await simulate.mutateAsync(day);
    } catch {
      Alert.alert("Erro", "Falha ao simular.");
    }
  }

  return (
    <View style={styles.container}>
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium">Vencimento Atual</Text>
          <Text variant="headlineMedium">Dia {me?.due_day ?? "—"}</Text>
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium">Novo Dia de Vencimento</Text>
          <TextInput
            value={newDueDay}
            onChangeText={setNewDueDay}
            keyboardType="numeric"
            maxLength={2}
            mode="outlined"
            placeholder="Ex: 15"
            style={styles.input}
          />
          <Button mode="contained" onPress={() => void handleSimulate()} loading={simulate.isPending} disabled={simulate.isPending}>
            Simular
          </Button>
        </Card.Content>
      </Card>

      {simulate.data && (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="titleMedium">Resultado</Text>
            <Text variant="bodyMedium">Diferença: {simulate.data.days_difference} dias</Text>
            <Text variant="bodyMedium">Taxa diária: R$ {simulate.data.daily_rate}</Text>
            <Text variant="headlineSmall" style={styles.fee}>
              Taxa de mudança: R$ {simulate.data.fee}
            </Text>
          </Card.Content>
        </Card>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, gap: 16 },
  card: { borderRadius: 12 },
  input: { marginVertical: 12 },
  fee: { marginTop: 8, color: "#E65100" },
});
```

- [ ] **Step 2: Implement rent adjustments history screen**

Create `mobile/app/(tenant)/payments/adjustments.tsx`:

```typescript
import { FlatList, StyleSheet, View } from "react-native";
import { ActivityIndicator, Card, Text } from "react-native-paper";
import { useTenantAdjustments } from "@/lib/api/hooks/use-tenant";

export default function AdjustmentsScreen() {
  const { data: adjustments, isLoading } = useTenantAdjustments();

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <FlatList
      style={styles.container}
      contentContainerStyle={styles.content}
      data={adjustments}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="titleMedium">
              {new Date(item.adjustment_date).toLocaleDateString("pt-BR")}
            </Text>
            <Text variant="bodyMedium">
              R$ {item.previous_value} → R$ {item.new_value} ({item.percentage}%)
            </Text>
          </Card.Content>
        </Card>
      )}
      ListEmptyComponent={
        <Text variant="bodyMedium" style={styles.empty}>
          Nenhum reajuste registrado.
        </Text>
      }
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 16, gap: 8 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center" },
  card: { borderRadius: 8 },
  empty: { textAlign: "center", color: "gray", marginTop: 32 },
});
```

- [ ] **Step 3: Commit**

```bash
git add mobile/app/(tenant)/payments/simulate.tsx mobile/app/(tenant)/payments/adjustments.tsx
git commit -m "feat(mobile): add due date simulation and rent adjustments screens"
```

---

## Task 8: Contract Screen

**Files:**
- Create: `mobile/app/(tenant)/contract.tsx`

- [ ] **Step 1: Implement contract screen**

Create `mobile/app/(tenant)/contract.tsx`:

```typescript
import { useState } from "react";
import { Alert, Linking, ScrollView, StyleSheet, View } from "react-native";
import { ActivityIndicator, Button, Card, Text } from "react-native-paper";
import { useTenantMe } from "@/lib/api/hooks/use-tenant";
import { apiClient } from "@/lib/api/client";
import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";

export default function ContractScreen() {
  const { data: me, isLoading } = useTenantMe();
  const [downloading, setDownloading] = useState(false);

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  const lease = me?.lease;
  const apartment = me?.apartment;

  async function handleDownloadContract(): Promise<void> {
    setDownloading(true);
    try {
      const response = await apiClient.get<ArrayBuffer>("/tenant/contract/", {
        responseType: "arraybuffer",
      });
      const fileUri = `${FileSystem.documentDirectory}contrato.pdf`;
      await FileSystem.writeAsStringAsync(fileUri, arrayBufferToBase64(response.data), {
        encoding: FileSystem.EncodingType.Base64,
      });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(fileUri, { mimeType: "application/pdf" });
      } else {
        Alert.alert("Sucesso", "Contrato salvo com sucesso.");
      }
    } catch {
      Alert.alert("Erro", "Não foi possível baixar o contrato.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {!lease ? (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="titleMedium">Sem locação ativa</Text>
          </Card.Content>
        </Card>
      ) : (
        <>
          <Card style={styles.card}>
            <Card.Content>
              <Text variant="titleMedium">Dados do Imóvel</Text>
              <View style={styles.infoGrid}>
                <InfoRow label="Apartamento" value={String(apartment?.number ?? "—")} />
                <InfoRow label="Prédio" value={apartment?.building_name ?? "—"} />
                <InfoRow label="Endereço" value={apartment?.building_address ?? "—"} />
              </View>
            </Card.Content>
          </Card>

          <Card style={styles.card}>
            <Card.Content>
              <Text variant="titleMedium">Dados do Contrato</Text>
              <View style={styles.infoGrid}>
                <InfoRow label="Início" value={new Date(lease.start_date).toLocaleDateString("pt-BR")} />
                <InfoRow label="Duração" value={`${lease.validity_months} meses`} />
                <InfoRow label="Valor" value={`R$ ${lease.rental_value}`} />
                {lease.pending_rental_value && (
                  <InfoRow label="Próximo valor" value={`R$ ${lease.pending_rental_value}`} />
                )}
                <InfoRow label="Ocupantes" value={String(lease.number_of_tenants)} />
              </View>
            </Card.Content>
          </Card>

          {lease.contract_generated && (
            <Button
              mode="contained"
              onPress={() => void handleDownloadContract()}
              loading={downloading}
              disabled={downloading}
              icon="file-download"
              style={styles.button}
            >
              Ver Contrato (PDF)
            </Button>
          )}
        </>
      )}
    </ScrollView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={infoStyles.row}>
      <Text variant="bodySmall" style={infoStyles.label}>
        {label}
      </Text>
      <Text variant="bodyMedium">{value}</Text>
    </View>
  );
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 16, gap: 16 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center" },
  card: { borderRadius: 12 },
  infoGrid: { marginTop: 12, gap: 8 },
  button: { marginTop: 8 },
});

const infoStyles = StyleSheet.create({
  row: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 4 },
  label: { color: "gray" },
});
```

- [ ] **Step 2: Commit**

```bash
git add mobile/app/(tenant)/contract.tsx
git commit -m "feat(mobile): add contract screen with PDF download and property data"
```

---

## Task 9: Profile Screen

**Files:**
- Create: `mobile/app/(tenant)/profile.tsx`

- [ ] **Step 1: Implement profile screen with logout**

Create `mobile/app/(tenant)/profile.tsx`:

```typescript
import { Alert, ScrollView, StyleSheet, View } from "react-native";
import { ActivityIndicator, Button, Card, Divider, Text } from "react-native-paper";
import { useTenantMe } from "@/lib/api/hooks/use-tenant";
import { useAuthStore } from "@/store/auth-store";
import { queryClient } from "@/lib/query-client";

export default function ProfileScreen() {
  const { data: me, isLoading } = useTenantMe();
  const { clearAuth } = useAuthStore();

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  function handleLogout(): void {
    Alert.alert("Sair", "Deseja realmente sair da conta?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Sair",
        style: "destructive",
        onPress: async () => {
          queryClient.clear();
          await clearAuth();
        },
      },
    ]);
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium">Dados Pessoais</Text>
          <View style={styles.infoGrid}>
            <InfoRow label="Nome" value={me?.name ?? "—"} />
            <InfoRow label="CPF/CNPJ" value={me?.cpf_cnpj ?? "—"} />
            <InfoRow label="Telefone" value={me?.phone ?? "—"} />
            <InfoRow label="Estado Civil" value={me?.marital_status ?? "—"} />
            <InfoRow label="Profissão" value={me?.profession ?? "—"} />
            <InfoRow label="RG" value={me?.rg ?? "—"} />
          </View>
        </Card.Content>
      </Card>

      {me?.dependents && me.dependents.length > 0 && (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="titleMedium">Dependentes</Text>
            {me.dependents.map((dep) => (
              <View key={dep.id} style={styles.depItem}>
                <Text variant="bodyMedium" style={styles.bold}>
                  {dep.name}
                </Text>
                {dep.phone && (
                  <Text variant="bodySmall" style={styles.muted}>
                    Tel: {dep.phone}
                  </Text>
                )}
                {dep.cpf_cnpj && (
                  <Text variant="bodySmall" style={styles.muted}>
                    CPF/CNPJ: {dep.cpf_cnpj}
                  </Text>
                )}
              </View>
            ))}
          </Card.Content>
        </Card>
      )}

      <Divider style={styles.divider} />

      <Button mode="outlined" onPress={handleLogout} textColor="#D32F2F" icon="logout" style={styles.logoutButton}>
        Sair da Conta
      </Button>
    </ScrollView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={infoStyles.row}>
      <Text variant="bodySmall" style={infoStyles.label}>
        {label}
      </Text>
      <Text variant="bodyMedium">{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 16, gap: 16 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center" },
  card: { borderRadius: 12 },
  infoGrid: { marginTop: 12, gap: 8 },
  bold: { fontWeight: "bold" },
  muted: { color: "gray" },
  depItem: { marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: "#eee" },
  divider: { marginVertical: 8 },
  logoutButton: { borderColor: "#D32F2F" },
});

const infoStyles = StyleSheet.create({
  row: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 4 },
  label: { color: "gray" },
});
```

- [ ] **Step 2: Commit**

```bash
git add mobile/app/(tenant)/profile.tsx
git commit -m "feat(mobile): add tenant profile screen with personal data, dependents, and logout"
```

---

## Self-Review Checklist

### Spec Coverage
- [x] Home: próximo vencimento, valor, status — Task 4
- [x] Home: alerta reajuste pendente — Task 4
- [x] Home: alertas/avisos (notificações não lidas) — Task 4
- [x] Home: atalho rápido para pagar — Task 4
- [x] Pagamentos: histórico — Task 5
- [x] Pagamentos: gerar PIX + QR code — Task 6
- [x] Pagamentos: enviar comprovante (foto + PDF) — Task 6
- [x] Pagamentos: simular troca vencimento — Task 7
- [x] Pagamentos: histórico reajustes — Task 7
- [x] Contrato: ver PDF — Task 8
- [x] Contrato: dados do imóvel — Task 8
- [x] Contrato: vencimento do contrato — Task 8
- [x] Perfil: dados cadastrais — Task 9
- [x] Perfil: dependentes — Task 9
- [x] Perfil: logout — Task 9
- [x] Tenant inativo: mensagem "contrato encerrado" — Task 4 (card "Sem locação ativa")
- [x] expo-image-picker + expo-document-picker — Task 1 (deps) + Task 6 (usage)
- [x] react-native-qrcode-svg — Task 1 (deps) + Task 6 (usage)

### Not in this plan
- Push notifications setup (Plan 5)
- Notification preferences in profile (Plan 5)
