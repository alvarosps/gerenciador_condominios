import { ScrollView, StyleSheet, View } from "react-native";
import { Button, Card, Chip, Text } from "react-native-paper";
import { useState } from "react";
import { useMonthlyPurchases } from "@/lib/api/hooks/use-admin-financial";

type PurchaseType = "card_purchases" | "loans" | "utility_bills" | "one_time_expenses" | "fixed_expenses";

const PURCHASE_TYPE_LABELS: Record<PurchaseType, string> = {
  card_purchases: "Cartão de Crédito",
  loans: "Empréstimos",
  utility_bills: "Contas Fixas",
  one_time_expenses: "Despesas Avulsas",
  fixed_expenses: "Despesas Recorrentes",
};

const PURCHASE_TYPE_COLORS: Record<PurchaseType, string> = {
  card_purchases: "#E3F2FD",
  loans: "#FFEBEE",
  utility_bills: "#FFF8E1",
  one_time_expenses: "#F3E5F5",
  fixed_expenses: "#E8F5E9",
};

const PURCHASE_TYPE_TEXT_COLORS: Record<PurchaseType, string> = {
  card_purchases: "#1565C0",
  loans: "#C62828",
  utility_bills: "#E65100",
  one_time_expenses: "#6A1B9A",
  fixed_expenses: "#2E7D32",
};

export default function MonthlyPurchasesScreen() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const { data: purchases, isLoading } = useMonthlyPurchases(year, month);

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

  const purchaseTypes: PurchaseType[] = [
    "card_purchases",
    "loans",
    "utility_bills",
    "one_time_expenses",
    "fixed_expenses",
  ];

  const grandTotal = purchaseTypes.reduce((sum, key) => {
    const group = purchases?.[key];
    return sum + (group ? parseFloat(group.total) : 0);
  }, 0);

  return (
    <ScrollView contentContainerStyle={styles.container}>
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

      <Card style={styles.totalCard}>
        <Card.Content style={styles.totalContent}>
          <Text variant="titleMedium">Total do Mês</Text>
          <Chip style={styles.totalChip} textStyle={styles.totalText}>
            {isLoading ? "..." : formatCurrency(grandTotal.toFixed(2))}
          </Chip>
        </Card.Content>
      </Card>

      {isLoading ? (
        <View style={styles.center}>
          <Text variant="bodyMedium">Carregando...</Text>
        </View>
      ) : (
        purchaseTypes.map((key) => {
          const group = purchases?.[key];
          return (
            <Card
              key={key}
              style={[styles.card, { backgroundColor: PURCHASE_TYPE_COLORS[key] }]}
            >
              <Card.Content style={styles.typeContent}>
                <View style={styles.typeHeader}>
                  <Text variant="titleSmall" style={{ color: PURCHASE_TYPE_TEXT_COLORS[key] }}>
                    {PURCHASE_TYPE_LABELS[key]}
                  </Text>
                  <Chip
                    compact
                    style={{ backgroundColor: PURCHASE_TYPE_TEXT_COLORS[key] + "22" }}
                    textStyle={{ color: PURCHASE_TYPE_TEXT_COLORS[key] }}
                  >
                    {group?.count ?? 0} itens
                  </Chip>
                </View>
                <Text
                  variant="headlineSmall"
                  style={[styles.typeTotal, { color: PURCHASE_TYPE_TEXT_COLORS[key] }]}
                >
                  {group ? formatCurrency(group.total) : "R$ 0,00"}
                </Text>
              </Card.Content>
            </Card>
          );
        })
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  navigator: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  monthLabel: { fontWeight: "600" },
  totalCard: { borderRadius: 8 },
  totalContent: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  totalChip: { backgroundColor: "#E3F2FD" },
  totalText: { color: "#1565C0", fontWeight: "700" },
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: 16 },
  card: { borderRadius: 8 },
  typeContent: { gap: 8 },
  typeHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  typeTotal: { fontWeight: "700" },
});
