import { Stack } from "expo-router";

export default function ActionsStackLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: "Ações" }} />
      <Stack.Screen name="mark-paid" options={{ title: "Marcar Aluguel Pago" }} />
      <Stack.Screen name="proofs" options={{ title: "Comprovantes" }} />
      <Stack.Screen name="rent-adjustment" options={{ title: "Reajuste de Aluguel" }} />
    </Stack>
  );
}
