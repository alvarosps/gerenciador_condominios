import { Tabs } from "expo-router";
import FontAwesome from "@expo/vector-icons/FontAwesome";

export default function TenantTabLayout() {
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
    </Tabs>
  );
}
