import { Redirect, Tabs } from "expo-router";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useAuthStore } from "@/store/auth-store";

export default function TenantTabLayout() {
  const { isAuthenticated, role } = useAuthStore();

  if (!isAuthenticated) return <Redirect href="/login" />;
  if (role !== "tenant") return <Redirect href="/(admin)" />;

  return (
    <Tabs
      screenOptions={{ tabBarActiveTintColor: "#2196F3", tabBarInactiveTintColor: "gray" }}
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
