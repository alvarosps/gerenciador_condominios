import { Tabs } from "expo-router";
import FontAwesome from "@expo/vector-icons/FontAwesome";

export default function AdminTabLayout() {
  return (
    <Tabs
      screenOptions={{ tabBarActiveTintColor: "#2196F3", tabBarInactiveTintColor: "gray" }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Dashboard",
          tabBarIcon: ({ color }) => (
            <FontAwesome name="dashboard" size={24} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="properties"
        options={{
          title: "Imóveis",
          headerShown: false,
          tabBarIcon: ({ color }) => (
            <FontAwesome name="building" size={24} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="financial"
        options={{
          title: "Financeiro",
          headerShown: false,
          tabBarIcon: ({ color }) => (
            <FontAwesome name="money" size={24} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="actions"
        options={{
          title: "Ações",
          headerShown: false,
          tabBarIcon: ({ color }) => (
            <FontAwesome name="bolt" size={24} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="notifications"
        options={{
          title: "Alertas",
          tabBarIcon: ({ color }) => (
            <FontAwesome name="bell" size={24} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
