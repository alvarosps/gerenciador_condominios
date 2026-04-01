import { Alert, ScrollView, StyleSheet, View } from "react-native";
import { Button, Card, Switch, Text, TextInput } from "react-native-paper";
import { useState } from "react";
import { useRentAdjustmentAlerts } from "@/lib/api/hooks/use-admin-dashboard";
import { useApplyRentAdjustment } from "@/lib/api/hooks/use-admin-actions";
import type { RentAdjustmentAlert } from "@/lib/schemas/admin";

export default function RentAdjustmentScreen() {
  const [selectedAlert, setSelectedAlert] = useState<RentAdjustmentAlert | null>(null);
  const [percentage, setPercentage] = useState("");
  const [adjustmentDate, setAdjustmentDate] = useState("");
  const [updateApartmentPrice, setUpdateApartmentPrice] = useState(true);

  const { data: alerts, isLoading } = useRentAdjustmentAlerts();
  const applyAdjustment = useApplyRentAdjustment();

  function handleSubmit(): void {
    if (selectedAlert === null) {
      Alert.alert("Erro", "Selecione uma locação.");
      return;
    }
    if (!percentage) {
      Alert.alert("Erro", "Informe o percentual de reajuste.");
      return;
    }
    if (!adjustmentDate) {
      Alert.alert("Erro", "Informe a data do reajuste (YYYY-MM-DD).");
      return;
    }

    Alert.alert(
      "Confirmar Reajuste",
      `Aplicar ${percentage}% na locação do apto ${selectedAlert.apartment_number} (${selectedAlert.tenant_name})?`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Confirmar",
          onPress: () => {
            applyAdjustment.mutate(
              {
                lease_id: selectedAlert.lease_id,
                percentage,
                renewal_date: adjustmentDate,
                update_apartment_prices: updateApartmentPrice,
              },
              {
                onSuccess: () => {
                  Alert.alert("Sucesso", "Reajuste aplicado com sucesso.");
                  setSelectedAlert(null);
                  setPercentage("");
                  setAdjustmentDate("");
                },
                onError: () => Alert.alert("Erro", "Não foi possível aplicar o reajuste."),
              },
            );
          },
        },
      ],
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Card style={styles.card}>
        <Card.Title title="Locações Elegíveis" />
        <Card.Content>
          {isLoading ? (
            <Text variant="bodySmall" style={styles.subText}>
              Carregando...
            </Text>
          ) : !alerts || alerts.length === 0 ? (
            <Text variant="bodySmall" style={styles.subText}>
              Nenhuma locação elegível para reajuste.
            </Text>
          ) : (
            <View style={styles.alertList}>
              {alerts.map((alert) => (
                <Button
                  key={alert.lease_id}
                  mode={selectedAlert?.lease_id === alert.lease_id ? "contained" : "outlined"}
                  style={styles.alertButton}
                  onPress={() => setSelectedAlert(alert)}
                >
                  Apto {alert.apartment_number} — {alert.tenant_name} ({alert.months_since_adjustment} meses)
                </Button>
              ))}
            </View>
          )}
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Title title="Dados do Reajuste" />
        <Card.Content style={styles.formContent}>
          <TextInput
            label="Percentual (%)"
            value={percentage}
            onChangeText={setPercentage}
            mode="outlined"
            keyboardType="decimal-pad"
            placeholder="5.00"
            style={styles.input}
          />
          <TextInput
            label="Data do reajuste (YYYY-MM-DD)"
            value={adjustmentDate}
            onChangeText={setAdjustmentDate}
            mode="outlined"
            placeholder="2026-04-01"
            style={styles.input}
          />
          <View style={styles.switchRow}>
            <Text variant="bodyMedium">Atualizar preços do apartamento</Text>
            <Switch
              value={updateApartmentPrice}
              onValueChange={setUpdateApartmentPrice}
            />
          </View>
        </Card.Content>
      </Card>

      <Button
        mode="contained"
        onPress={handleSubmit}
        loading={applyAdjustment.isPending}
        disabled={applyAdjustment.isPending}
        style={styles.submitButton}
      >
        Aplicar Reajuste
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  card: { borderRadius: 8 },
  alertList: { gap: 8 },
  alertButton: { marginBottom: 4 },
  formContent: { gap: 8 },
  input: { backgroundColor: "white" },
  switchRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 4 },
  subText: { color: "gray" },
  submitButton: { marginTop: 8 },
});
