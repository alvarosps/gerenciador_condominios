import { Alert, ScrollView, StyleSheet, View } from "react-native";
import { Button, Card, Text, TextInput } from "react-native-paper";
import { useState } from "react";
import { useLeases } from "@/lib/api/hooks/use-admin-properties";
import { useToggleRentPayment } from "@/lib/api/hooks/use-admin-actions";
import type { LeaseSimple } from "@/lib/schemas/admin";
import axios from "axios";

export default function MarkPaidScreen() {
  const [selectedLease, setSelectedLease] = useState<LeaseSimple | null>(null);
  const [referenceMonth, setReferenceMonth] = useState("");

  const { data: leases, isLoading } = useLeases({ is_active: true });
  const togglePayment = useToggleRentPayment();

  function handleSubmit(): void {
    if (selectedLease === null) {
      Alert.alert("Erro", "Selecione uma locação.");
      return;
    }
    if (!referenceMonth) {
      Alert.alert("Erro", "Informe o mês de referência (YYYY-MM-DD).");
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(referenceMonth)) {
      Alert.alert(
        "Erro",
        "Mês de referência inválido. Use o formato YYYY-MM-DD (ex.: 2026-04-01).",
      );
      return;
    }

    togglePayment.mutate(
      {
        lease_id: selectedLease.id,
        reference_month: referenceMonth,
      },
      {
        onSuccess: (result) => {
          // result.message differentiates "marcado como pago" vs "marcado como não pago"
          // (this endpoint is a toggle), so the actual effect is always shown.
          Alert.alert("Sucesso", result.message);
          setSelectedLease(null);
          setReferenceMonth("");
        },
        onError: (error) => {
          // Surface the backend's specific rejection (mês finalizado / não cobrável /
          // vencimento já passou) instead of a generic message.
          const detail =
            axios.isAxiosError(error) && typeof error.response?.data?.error === "string"
              ? error.response.data.error
              : "Não foi possível atualizar o pagamento.";
          Alert.alert("Erro", detail);
        },
      },
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Card style={styles.card}>
        <Card.Title title="Selecionar Locação" />
        <Card.Content>
          {isLoading ? (
            <Text variant="bodySmall" style={styles.subText}>
              Carregando...
            </Text>
          ) : !leases || leases.length === 0 ? (
            <Text variant="bodySmall" style={styles.subText}>
              Nenhuma locação ativa encontrada.
            </Text>
          ) : (
            <View style={styles.leaseList}>
              {leases.map((lease) => (
                <Button
                  key={lease.id}
                  mode={selectedLease?.id === lease.id ? "contained" : "outlined"}
                  style={styles.leaseButton}
                  onPress={() => setSelectedLease(lease)}
                >
                  Apto {lease.apartment} — {lease.responsible_tenant.name}
                </Button>
              ))}
            </View>
          )}
          {selectedLease !== null && (
            <Text variant="bodySmall" style={styles.selectedText}>
              Aluguel: R${" "}
              {parseFloat(selectedLease.rental_value).toFixed(2).replace(".", ",")}
            </Text>
          )}
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Title title="Mês de Referência" />
        <Card.Content style={styles.formContent}>
          <TextInput
            label="Mês de referência (YYYY-MM-DD)"
            value={referenceMonth}
            onChangeText={setReferenceMonth}
            mode="outlined"
            placeholder="2026-04-01"
            style={styles.input}
          />
        </Card.Content>
      </Card>

      <Button
        mode="contained"
        onPress={handleSubmit}
        loading={togglePayment.isPending}
        disabled={togglePayment.isPending}
        style={styles.submitButton}
      >
        Registrar Pagamento
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  card: { borderRadius: 8 },
  leaseList: { gap: 8 },
  leaseButton: { marginBottom: 4 },
  selectedText: { color: "#2E7D32", marginTop: 8 },
  formContent: { gap: 8 },
  input: { backgroundColor: "white" },
  subText: { color: "gray" },
  submitButton: { marginTop: 8 },
});
