import { FlatList, StyleSheet, View } from "react-native";
import { Button, Card, Divider, Text } from "react-native-paper";
import { useRouter } from "expo-router";
import { useTenantPayments } from "@/lib/api/hooks/use-tenant";
import type { RentPayment } from "@/lib/schemas/tenant";

function PaymentItem({ item }: { item: RentPayment }) {
  const [year, month] = item.reference_month.split("-");
  return (
    <View style={styles.itemContainer}>
      <View style={styles.itemRow}>
        <Text variant="bodyMedium" style={styles.itemMonth}>
          {month}/{year}
        </Text>
        <Text variant="bodyMedium">
          R$ {parseFloat(item.amount_paid).toFixed(2).replace(".", ",")}
        </Text>
      </View>
      <Text variant="bodySmall" style={styles.itemDate}>
        Pago em{" "}
        {new Date(item.payment_date + "T12:00:00").toLocaleDateString("pt-BR")}
      </Text>
      <Divider style={styles.divider} />
    </View>
  );
}

export default function PaymentsScreen() {
  const router = useRouter();
  const { data: payments, isLoading } = useTenantPayments();

  return (
    <View style={styles.container}>
      <View style={styles.actions}>
        <Button
          mode="contained"
          onPress={() => router.push("/(tenant)/payments/pix")}
          style={styles.actionButton}
        >
          Pagar Aluguel
        </Button>
        <Button
          mode="outlined"
          onPress={() => router.push("/(tenant)/payments/simulate")}
          style={styles.actionButton}
        >
          Simular Vencimento
        </Button>
        <Button
          mode="outlined"
          onPress={() => router.push("/(tenant)/payments/adjustments")}
          style={styles.actionButton}
        >
          Reajustes
        </Button>
      </View>

      <Card style={styles.listCard}>
        <Card.Title title="Histórico de Pagamentos" />
        <Card.Content>
          {isLoading ? (
            <Text variant="bodyMedium">Carregando...</Text>
          ) : !payments || payments.length === 0 ? (
            <Text variant="bodyMedium" style={styles.emptyText}>
              Nenhum pagamento registrado.
            </Text>
          ) : (
            <FlatList
              data={payments}
              keyExtractor={(item) => String(item.id)}
              renderItem={({ item }) => <PaymentItem item={item} />}
              scrollEnabled={false}
            />
          )}
        </Card.Content>
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  actions: { gap: 8, marginBottom: 16 },
  actionButton: {},
  listCard: { borderRadius: 8 },
  itemContainer: {},
  itemRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 8 },
  itemMonth: { fontWeight: "600" },
  itemDate: { color: "gray", marginBottom: 4 },
  divider: { marginTop: 4 },
  emptyText: { color: "gray" },
});
