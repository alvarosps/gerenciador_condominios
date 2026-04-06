import { Alert, ScrollView, StyleSheet, View } from "react-native";
import { Button, Card, Divider, Text } from "react-native-paper";
import { useAuthStore } from "@/store/auth-store";
import { queryClient } from "@/lib/query-client";
import { useTenantMe } from "@/lib/api/hooks/use-tenant";

export default function ProfileScreen() {
  const { clearAuth } = useAuthStore();
  const { data: tenant, isLoading } = useTenantMe();

  function handleLogout(): void {
    Alert.alert("Sair", "Deseja realmente sair da sua conta?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Sair",
        style: "destructive",
        onPress: () => {
          queryClient.clear();
          void clearAuth();
        },
      },
    ]);
  }

  if (isLoading) {
    return (
      <ScrollView contentContainerStyle={styles.container}>
        <Text variant="bodyMedium">Carregando...</Text>
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Card style={styles.card}>
        <Card.Title title="Dados Pessoais" />
        <Card.Content>
          <Text variant="bodyMedium">
            <Text style={styles.label}>Nome: </Text>
            {tenant?.name ?? "—"}
          </Text>
          <Text variant="bodyMedium">
            <Text style={styles.label}>CPF/CNPJ: </Text>
            {tenant?.cpf_cnpj ?? "—"}
          </Text>
          <Text variant="bodyMedium">
            <Text style={styles.label}>Telefone: </Text>
            {tenant?.phone ?? "—"}
          </Text>
          <Text variant="bodyMedium">
            <Text style={styles.label}>Estado civil: </Text>
            {tenant?.marital_status ?? "—"}
          </Text>
          <Text variant="bodyMedium">
            <Text style={styles.label}>Profissão: </Text>
            {tenant?.profession ?? "—"}
          </Text>
          <Text variant="bodyMedium">
            <Text style={styles.label}>RG: </Text>
            {tenant?.rg ?? "—"}
          </Text>
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Title title="Dependentes" />
        <Card.Content>
          {!tenant?.dependents || tenant.dependents.length === 0 ? (
            <Text variant="bodyMedium" style={styles.emptyText}>
              Nenhum dependente cadastrado.
            </Text>
          ) : (
            tenant.dependents.map((dep, index) => (
              <View key={dep.id}>
                <Text variant="bodyMedium" style={styles.depName}>
                  {dep.name}
                </Text>
                {dep.phone ? (
                  <Text variant="bodySmall" style={styles.depDetail}>
                    Tel: {dep.phone}
                  </Text>
                ) : null}
                {dep.cpf_cnpj ? (
                  <Text variant="bodySmall" style={styles.depDetail}>
                    CPF: {dep.cpf_cnpj}
                  </Text>
                ) : null}
                {index < tenant.dependents.length - 1 && <Divider style={styles.divider} />}
              </View>
            ))
          )}
        </Card.Content>
      </Card>

      <Button
        mode="outlined"
        onPress={handleLogout}
        textColor="#C62828"
        style={styles.logoutButton}
      >
        Sair
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 16 },
  card: { borderRadius: 8 },
  label: { fontWeight: "600" },
  emptyText: { color: "gray" },
  depName: { fontWeight: "600", marginTop: 4 },
  depDetail: { color: "gray" },
  divider: { marginVertical: 8 },
  logoutButton: { borderColor: "#C62828" },
});
