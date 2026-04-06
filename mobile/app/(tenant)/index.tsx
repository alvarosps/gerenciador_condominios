import { ScrollView, StyleSheet, View } from "react-native";
import { Button, Card, Text } from "react-native-paper";
import { useRouter } from "expo-router";
import { useTenantMe } from "@/lib/api/hooks/use-tenant";
import { useTenantNotifications } from "@/lib/api/hooks/use-tenant-notifications";

export default function TenantHome() {
  const router = useRouter();
  const { data: tenant, isLoading } = useTenantMe();
  const { data: notifications } = useTenantNotifications();

  const unreadNotifications = notifications?.filter((n) => !n.is_read).slice(0, 3) ?? [];

  if (isLoading) {
    return (
      <View style={styles.center}>
        <Text variant="bodyMedium">Carregando...</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text variant="headlineSmall" style={styles.greeting}>
        Olá, {tenant?.name ?? "Inquilino"}
      </Text>

      {tenant?.lease && tenant.apartment ? (
        <>
          <Card style={styles.card}>
            <Card.Content>
              <Text variant="titleMedium" style={styles.cardTitle}>
                Próximo Pagamento
              </Text>
              <Text variant="bodyLarge">
                R$ {parseFloat(tenant.lease.rental_value).toFixed(2).replace(".", ",")}
              </Text>
              <Text variant="bodyMedium" style={styles.subText}>
                Vencimento: dia {tenant.due_day}
              </Text>
              <Text variant="bodyMedium" style={styles.subText}>
                Apto {tenant.apartment.number} — {tenant.apartment.building_name}
              </Text>
            </Card.Content>
            <Card.Actions>
              <Button
                mode="contained"
                onPress={() => router.push("/(tenant)/payments/pix")}
              >
                Pagar
              </Button>
            </Card.Actions>
          </Card>

          {tenant.lease.pending_rental_value !== null && (
            <Card style={[styles.card, styles.alertCard]}>
              <Card.Content>
                <Text variant="titleSmall" style={styles.alertTitle}>
                  Novo valor pendente
                </Text>
                <Text variant="bodyMedium">
                  A partir de {tenant.lease.pending_rental_value_date ?? "em breve"}, o aluguel
                  passará para R${" "}
                  {parseFloat(tenant.lease.pending_rental_value).toFixed(2).replace(".", ",")}
                </Text>
              </Card.Content>
            </Card>
          )}
        </>
      ) : (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="titleMedium">Sem locação ativa</Text>
            <Text variant="bodyMedium" style={styles.subText}>
              Não há contrato de locação ativo no momento.
            </Text>
          </Card.Content>
        </Card>
      )}

      {unreadNotifications.length > 0 && (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="titleMedium" style={styles.cardTitle}>
              Notificações
            </Text>
            {unreadNotifications.map((n) => (
              <View key={n.id} style={styles.notificationItem}>
                <Text variant="bodyMedium" style={styles.notifTitle}>
                  {n.title}
                </Text>
                <Text variant="bodySmall" style={styles.subText}>
                  {n.body}
                </Text>
              </View>
            ))}
          </Card.Content>
        </Card>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  greeting: { marginBottom: 4 },
  card: { borderRadius: 8 },
  alertCard: { backgroundColor: "#FFF8E1" },
  cardTitle: { marginBottom: 8 },
  alertTitle: { color: "#E65100", marginBottom: 4 },
  subText: { color: "gray", marginTop: 2 },
  notificationItem: { marginTop: 8 },
  notifTitle: { fontWeight: "600" },
});
