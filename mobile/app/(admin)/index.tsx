import { ScrollView, StyleSheet, View } from "react-native";
import { Card, Text } from "react-native-paper";
import { useRouter } from "expo-router";
import { useFinancialSummary, useLatePayments, useLeaseMetrics, useRentAdjustmentAlerts } from "@/lib/api/hooks/use-admin-dashboard";
import { useAdminProofs } from "@/lib/api/hooks/use-admin-actions";

export default function AdminDashboard() {
  const router = useRouter();
  const { data: financialSummary, isLoading: loadingSummary } = useFinancialSummary();
  const { data: latePayments, isLoading: loadingLate } = useLatePayments();
  const { data: leaseMetrics, isLoading: loadingMetrics } = useLeaseMetrics();
  const { data: adjustmentAlerts } = useRentAdjustmentAlerts();
  const { data: pendingProofs } = useAdminProofs("pending");

  const isLoading = loadingSummary || loadingLate || loadingMetrics;

  if (isLoading) {
    return (
      <View style={styles.center}>
        <Text variant="bodyMedium">Carregando...</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text variant="headlineSmall" style={styles.heading}>
        Dashboard
      </Text>

      <Card
        style={styles.card}
        onPress={() => router.push("/(admin)/properties")}
      >
        <Card.Title title="Ocupação" />
        <Card.Content>
          <Text variant="headlineMedium" style={styles.highlight}>
            {financialSummary?.occupancy_rate !== undefined
              ? `${financialSummary.occupancy_rate.toFixed(1)}%`
              : "—"}
          </Text>
          <Text variant="bodyMedium" style={styles.subText}>
            {financialSummary?.rented_apartments ?? "—"} alugados de{" "}
            {financialSummary?.total_apartments ?? "—"} apartamentos
          </Text>
          <Text variant="bodySmall" style={styles.subText}>
            {financialSummary?.vacant_apartments ?? "—"} vagos
          </Text>
        </Card.Content>
      </Card>

      <Card
        style={[styles.card, (latePayments?.total_late ?? 0) > 0 && styles.alertCard]}
        onPress={() => router.push("/(admin)/actions/mark-paid")}
      >
        <Card.Title title="Aluguéis Atrasados" />
        <Card.Content>
          <Text
            variant="headlineMedium"
            style={[styles.highlight, (latePayments?.total_late ?? 0) > 0 && styles.alertText]}
          >
            {latePayments?.total_late ?? 0}
          </Text>
          <Text variant="bodyMedium" style={styles.subText}>
            Total em aberto: R${" "}
            {latePayments?.total_amount_due
              ? parseFloat(latePayments.total_amount_due).toFixed(2).replace(".", ",")
              : "0,00"}
          </Text>
        </Card.Content>
      </Card>

      <Card
        style={styles.card}
        onPress={() => router.push("/(admin)/properties")}
      >
        <Card.Title title="Locações" />
        <Card.Content>
          <View style={styles.metricsRow}>
            <View style={styles.metricItem}>
              <Text variant="headlineSmall" style={styles.metricValue}>
                {leaseMetrics?.active_leases ?? "—"}
              </Text>
              <Text variant="bodySmall" style={styles.subText}>
                Ativas
              </Text>
            </View>
            <View style={styles.metricItem}>
              <Text variant="headlineSmall" style={[styles.metricValue, styles.alertText]}>
                {leaseMetrics?.expiring_soon ?? "—"}
              </Text>
              <Text variant="bodySmall" style={styles.subText}>
                Vencendo
              </Text>
            </View>
            <View style={styles.metricItem}>
              <Text variant="headlineSmall" style={styles.metricValue}>
                {leaseMetrics?.expired_leases ?? "—"}
              </Text>
              <Text variant="bodySmall" style={styles.subText}>
                Expiradas
              </Text>
            </View>
          </View>
        </Card.Content>
      </Card>

      <Card
        style={[
          styles.card,
          (adjustmentAlerts?.length ?? 0) > 0 && styles.warningCard,
        ]}
        onPress={() => router.push("/(admin)/actions/rent-adjustment")}
      >
        <Card.Title title="Reajustes Pendentes" />
        <Card.Content>
          <Text
            variant="headlineMedium"
            style={[
              styles.highlight,
              (adjustmentAlerts?.length ?? 0) > 0 && styles.warningText,
            ]}
          >
            {adjustmentAlerts?.length ?? 0}
          </Text>
          <Text variant="bodySmall" style={styles.subText}>
            Locações elegíveis para reajuste
          </Text>
        </Card.Content>
      </Card>

      {(pendingProofs?.length ?? 0) > 0 && (
        <Card
          style={[styles.card, styles.infoCard]}
          onPress={() => router.push("/(admin)/actions/proofs")}
        >
          <Card.Title title="Comprovantes Pendentes" />
          <Card.Content>
            <Text variant="headlineMedium" style={[styles.highlight, styles.infoText]}>
              {pendingProofs?.length ?? 0}
            </Text>
            <Text variant="bodySmall" style={styles.subText}>
              Aguardando aprovação
            </Text>
          </Card.Content>
        </Card>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  heading: { marginBottom: 4 },
  card: { borderRadius: 8 },
  alertCard: { backgroundColor: "#FFEBEE" },
  warningCard: { backgroundColor: "#FFF8E1" },
  infoCard: { backgroundColor: "#E3F2FD" },
  highlight: { fontWeight: "700" },
  alertText: { color: "#C62828" },
  warningText: { color: "#E65100" },
  infoText: { color: "#1565C0" },
  subText: { color: "gray", marginTop: 2 },
  metricsRow: { flexDirection: "row", justifyContent: "space-around" },
  metricItem: { alignItems: "center" },
  metricValue: { fontWeight: "700" },
});
