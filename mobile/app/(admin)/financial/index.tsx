import { FlatList, ScrollView, StyleSheet, View } from "react-native";
import { Card, Divider, Text } from "react-native-paper";
import { useRouter } from "expo-router";
import {
  useFinancialOverview,
  useOverdueInstallments,
  useUpcomingInstallments,
} from "@/lib/api/hooks/use-admin-financial";

export default function FinancialDashboardScreen() {
  const router = useRouter();
  const { data: overview, isLoading: loadingOverview } = useFinancialOverview();
  const { data: upcoming, isLoading: loadingUpcoming } = useUpcomingInstallments(30);
  const { data: overdue, isLoading: loadingOverdue } = useOverdueInstallments();

  if (loadingOverview) {
    return (
      <View style={styles.center}>
        <Text variant="bodyMedium">Carregando...</Text>
      </View>
    );
  }

  function formatCurrency(value: string): string {
    return `R$ ${parseFloat(value).toFixed(2).replace(".", ",")}`;
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.overviewRow}>
        <Card style={[styles.overviewCard, styles.incomeCard]}>
          <Card.Content>
            <Text variant="labelSmall" style={styles.overviewLabel}>
              Receitas
            </Text>
            <Text variant="titleMedium" style={styles.incomeText}>
              {overview ? formatCurrency(overview.total_income) : "—"}
            </Text>
          </Card.Content>
        </Card>
        <Card style={[styles.overviewCard, styles.expenseCard]}>
          <Card.Content>
            <Text variant="labelSmall" style={styles.overviewLabel}>
              Despesas
            </Text>
            <Text variant="titleMedium" style={styles.expenseText}>
              {overview ? formatCurrency(overview.total_expenses) : "—"}
            </Text>
          </Card.Content>
        </Card>
      </View>

      <View style={styles.overviewRow}>
        <Card style={[styles.overviewCard, styles.balanceCard]}>
          <Card.Content>
            <Text variant="labelSmall" style={styles.overviewLabel}>
              Saldo
            </Text>
            <Text variant="titleMedium" style={styles.balanceText}>
              {overview ? formatCurrency(overview.balance) : "—"}
            </Text>
          </Card.Content>
        </Card>
        <Card style={[styles.overviewCard, styles.overdueCard]}>
          <Card.Content>
            <Text variant="labelSmall" style={styles.overviewLabel}>
              Vencido
            </Text>
            <Text variant="titleMedium" style={styles.overdueText}>
              {overview ? formatCurrency(overview.overdue_total) : "—"}
            </Text>
          </Card.Content>
        </Card>
      </View>

      <Card style={styles.card} onPress={() => router.push("/(admin)/financial/daily")}>
        <Card.Title title="Próximos Vencimentos (30 dias)" />
        <Card.Content>
          {loadingUpcoming ? (
            <Text variant="bodySmall" style={styles.subText}>
              Carregando...
            </Text>
          ) : !upcoming || upcoming.length === 0 ? (
            <Text variant="bodySmall" style={styles.subText}>
              Nenhum vencimento próximo.
            </Text>
          ) : (
            <FlatList
              data={upcoming.slice(0, 5)}
              keyExtractor={(item) => String(item.id)}
              scrollEnabled={false}
              ItemSeparatorComponent={() => <Divider style={styles.divider} />}
              renderItem={({ item }) => (
                <View style={styles.installmentRow}>
                  <View style={styles.installmentInfo}>
                    <Text variant="bodyMedium">{item.description}</Text>
                    {item.person_name !== null && (
                      <Text variant="bodySmall" style={styles.subText}>
                        {item.person_name}
                      </Text>
                    )}
                  </View>
                  <Text variant="bodyMedium" style={styles.expenseText}>
                    {formatCurrency(item.amount)}
                  </Text>
                </View>
              )}
            />
          )}
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Title title="Parcelas Vencidas" />
        <Card.Content>
          {loadingOverdue ? (
            <Text variant="bodySmall" style={styles.subText}>
              Carregando...
            </Text>
          ) : !overdue || overdue.length === 0 ? (
            <Text variant="bodySmall" style={styles.subText}>
              Nenhuma parcela vencida.
            </Text>
          ) : (
            <FlatList
              data={overdue.slice(0, 5)}
              keyExtractor={(item) => String(item.id)}
              scrollEnabled={false}
              ItemSeparatorComponent={() => <Divider style={styles.divider} />}
              renderItem={({ item }) => (
                <View style={styles.installmentRow}>
                  <View style={styles.installmentInfo}>
                    <Text variant="bodyMedium">{item.description}</Text>
                    <Text variant="bodySmall" style={styles.subText}>
                      Venc: {new Date(item.due_date + "T12:00:00").toLocaleDateString("pt-BR")}
                    </Text>
                  </View>
                  <Text variant="bodyMedium" style={styles.overdueText}>
                    {formatCurrency(item.amount)}
                  </Text>
                </View>
              )}
            />
          )}
        </Card.Content>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  overviewRow: { flexDirection: "row", gap: 8 },
  overviewCard: { flex: 1, borderRadius: 8 },
  overviewLabel: { color: "gray", marginBottom: 4 },
  incomeCard: { backgroundColor: "#E8F5E9" },
  expenseCard: { backgroundColor: "#FFEBEE" },
  balanceCard: { backgroundColor: "#E3F2FD" },
  overdueCard: { backgroundColor: "#FFF8E1" },
  incomeText: { color: "#2E7D32", fontWeight: "700" },
  expenseText: { color: "#C62828", fontWeight: "700" },
  balanceText: { color: "#1565C0", fontWeight: "700" },
  overdueText: { color: "#E65100", fontWeight: "700" },
  card: { borderRadius: 8 },
  installmentRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 6 },
  installmentInfo: { flex: 1 },
  subText: { color: "gray", marginTop: 2 },
  divider: { marginVertical: 2 },
});
