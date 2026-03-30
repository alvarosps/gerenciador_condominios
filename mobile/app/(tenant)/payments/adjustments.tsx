import { FlatList, StyleSheet, View } from "react-native";
import { Card, Divider, Text } from "react-native-paper";
import { useTenantAdjustments } from "@/lib/api/hooks/use-tenant";
import type { RentAdjustment } from "@/lib/schemas/tenant";

function AdjustmentItem({ item }: { item: RentAdjustment }) {
  const date = new Date(item.adjustment_date + "T12:00:00").toLocaleDateString("pt-BR");
  const percentage = parseFloat(item.percentage);
  const percentageLabel = `${percentage > 0 ? "+" : ""}${percentage.toFixed(2).replace(".", ",")}%`;
  const previous = `R$ ${parseFloat(item.previous_value).toFixed(2).replace(".", ",")}`;
  const next = `R$ ${parseFloat(item.new_value).toFixed(2).replace(".", ",")}`;

  return (
    <View style={styles.itemContainer}>
      <View style={styles.itemRow}>
        <Text variant="bodyMedium" style={styles.itemDate}>
          {date}
        </Text>
        <Text
          variant="bodyMedium"
          style={[styles.percentage, percentage >= 0 ? styles.increase : styles.decrease]}
        >
          {percentageLabel}
        </Text>
      </View>
      <Text variant="bodySmall" style={styles.values}>
        {previous} → {next}
      </Text>
      <Divider style={styles.divider} />
    </View>
  );
}

export default function AdjustmentsScreen() {
  const { data: adjustments, isLoading } = useTenantAdjustments();

  return (
    <Card style={styles.container}>
      <Card.Title title="Histórico de Reajustes" />
      <Card.Content>
        {isLoading ? (
          <Text variant="bodyMedium">Carregando...</Text>
        ) : !adjustments || adjustments.length === 0 ? (
          <Text variant="bodyMedium" style={styles.emptyText}>
            Nenhum reajuste registrado.
          </Text>
        ) : (
          <FlatList
            data={adjustments}
            keyExtractor={(item) => String(item.id)}
            renderItem={({ item }) => <AdjustmentItem item={item} />}
            scrollEnabled={false}
          />
        )}
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  container: { margin: 16, borderRadius: 8 },
  itemContainer: {},
  itemRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 8 },
  itemDate: { color: "gray" },
  percentage: { fontWeight: "700" },
  increase: { color: "#C62828" },
  decrease: { color: "#2E7D32" },
  values: { color: "gray", marginBottom: 4 },
  divider: { marginTop: 4 },
  emptyText: { color: "gray" },
});
