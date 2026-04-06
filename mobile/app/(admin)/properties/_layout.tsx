import { Stack } from "expo-router";

export default function PropertiesStackLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: "Imóveis" }} />
      <Stack.Screen name="[id]" options={{ title: "Apartamentos" }} />
      <Stack.Screen name="new-lease" options={{ title: "Nova Locação" }} />
    </Stack>
  );
}
