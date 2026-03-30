import { Stack } from "expo-router";

export default function PaymentsStackLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: "Pagamentos" }} />
      <Stack.Screen name="pix" options={{ title: "Pagar Aluguel" }} />
      <Stack.Screen name="simulate" options={{ title: "Simular Vencimento" }} />
      <Stack.Screen name="adjustments" options={{ title: "Reajustes" }} />
    </Stack>
  );
}
