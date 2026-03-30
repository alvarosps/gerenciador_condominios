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
    </Tabs>
  );
}
