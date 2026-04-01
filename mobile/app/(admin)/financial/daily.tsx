import { Alert, FlatList, StyleSheet, View } from "react-native";
import { Button, Card, Chip, Divider, Text } from "react-native-paper";
import { useState } from "react";
import { useDailyBreakdown, useDailySummary, useMarkDailyPaid } from "@/lib/api/hooks/use-admin-financial";

export default function DailyControlScreen() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const { data: breakdown, isLoading: loadingBreakdown } = useDailyBreakdown(year, month);
  const { data: summary, isLoading: loadingSummary } = useDailySummary(year, month);
  const markPaid = useMarkDailyPaid();

  function navigateMonth(delta: number): void {
    let newMonth = month + delta;
    let newYear = year;
    if (newMonth > 12) {
      newMonth = 1;
      newYear += 1;
    } else if (newMonth < 1) {
      newMonth = 12;
      newYear -= 1;
    }
    setMonth(newMonth);
    setYear(newYear);
  }

  function monthLabel(): string {
    const date = new Date(year, month - 1, 1);
    return date.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
  }

  function formatCurrency(value: string): string {
    return `R$ ${parseFloat(value).toFixed(2).replace(".", ",")}`;
  }

  function handleMarkPaid(id: number, type: string): void {
    markPaid.mutate(
      { item_id: id, item_type: type },
      {
        onError: () => Alert.alert("Erro", "Não foi possível marcar como pago."),
      },
    );
  }

  const isLoading = loadingBreakdown || loadingSummary;

  return (
    <View style={styles.container}>
      <View style={styles.navigator}>
        <Button mode="outlined" compact onPress={() => navigateMonth(-1)}>
          {"<"}
        </Button>
        <Text variant="titleMedium" style={styles.monthLabel}>
          {monthLabel()}
        </Text>
        <Button mode="outlined" compact onPress={() => navigateMonth(1)}>
          {">"}
        </Button>
      </View>

      {!loadingSummary && summary && (
        <View style={styles.summaryRow}>
          <Card style={[styles.summaryCard, styles.incomeCard]}>
            <Card.Content>
              <Text variant="labelSmall" style={styles.subText}>
                Entradas
              </Text>
              <Text variant="bodyMedium" style={styles.incomeText}>
                {formatCurrency(summary.actual_income)}
              </Text>
              <Text variant="bodySmall" style={styles.subText}>
                Prev: {formatCurrency(summary.expected_income)}
              </Text>
            </Card.Content>
          </Card>
          <Card style={[styles.summaryCard, styles.expenseCard]}>
            <Card.Content>
              <Text variant="labelSmall" style={styles.subText}>
                Saídas
              </Text>
              <Text variant="bodyMedium" style={styles.expenseText}>
                {formatCurrency(summary.actual_expenses)}
              </Text>
              <Text variant="bodySmall" style={styles.subText}>
                Prev: {formatCurrency(summary.expected_expenses)}
              </Text>
            </Card.Content>
          </Card>
        </View>
      )}

      {isLoading ? (
        <View style={styles.center}>
          <Text variant="bodyMedium">Carregando...</Text>
        </View>
      ) : !breakdown || breakdown.length === 0 ? (
        <View style={styles.center}>
          <Text variant="bodyMedium" style={styles.subText}>
            Nenhum lançamento neste mês.
          </Text>
        </View>
      ) : (
        <FlatList
          data={breakdown}
          keyExtractor={(item) => `${item.type}-${item.id}`}
          ItemSeparatorComponent={() => <Divider />}
          renderItem={({ item }) => (
            <View style={styles.itemRow}>
              <View style={styles.itemInfo}>
                <Text variant="bodyMedium">{item.description}</Text>
                <Text variant="bodySmall" style={styles.subText}>
                  {new Date(item.date + "T12:00:00").toLocaleDateString("pt-BR")}
                </Text>
              </View>
              <View style={styles.itemRight}>
                <Text
                  variant="bodyMedium"
                  style={item.type === "income" ? styles.incomeText : styles.expenseText}
                >
                  {formatCurrency(item.amount)}
                </Text>
                {item.is_paid ? (
                  <Chip compact style={styles.paidChip} textStyle={styles.paidText}>
                    Pago
                  </Chip>
                ) : (
                  <View style={styles.pendingRow}>
                    <Chip compact style={styles.pendingChip} textStyle={styles.pendingText}>
                      Pendente
                    </Chip>
                    <Button
                      mode="text"
                      compact
                      onPress={() => handleMarkPaid(item.id, item.type)}
                      disabled={markPaid.isPending}
                    >
                      Pagar
                    </Button>
                  </View>
                )}
              </View>
            </View>
          )}
          contentContainerStyle={styles.list}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f5f5" },
  navigator: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 16,
    backgroundColor: "white",
  },
  monthLabel: { fontWeight: "600" },
  summaryRow: { flexDirection: "row", gap: 8, paddingHorizontal: 16, paddingVertical: 8 },
  summaryCard: { flex: 1, borderRadius: 8 },
  incomeCard: { backgroundColor: "#E8F5E9" },
  expenseCard: { backgroundColor: "#FFEBEE" },
  incomeText: { color: "#2E7D32", fontWeight: "700" },
  expenseText: { color: "#C62828", fontWeight: "700" },
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: 16 },
  list: { paddingBottom: 16 },
  itemRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: "white",
  },
  itemInfo: { flex: 1 },
  itemRight: { alignItems: "flex-end", gap: 4 },
  paidChip: { backgroundColor: "#E8F5E9" },
  paidText: { color: "#2E7D32" },
  pendingChip: { backgroundColor: "#FFF8E1" },
  pendingText: { color: "#E65100" },
  pendingRow: { flexDirection: "row", alignItems: "center" },
  subText: { color: "gray", marginTop: 2 },
});
