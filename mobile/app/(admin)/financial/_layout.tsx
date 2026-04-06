import { Stack } from "expo-router";

export default function FinancialStackLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: "Financeiro" }} />
      <Stack.Screen name="daily" options={{ title: "Controle Diário" }} />
      <Stack.Screen name="purchases" options={{ title: "Compras do Mês" }} />
    </Stack>
  );
}
