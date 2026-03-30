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
