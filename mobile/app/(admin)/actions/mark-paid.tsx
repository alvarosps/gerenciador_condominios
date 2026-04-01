import { Alert, ScrollView, StyleSheet, View } from "react-native";
import { Button, Card, Text, TextInput } from "react-native-paper";
import { useState } from "react";
import { useLeases } from "@/lib/api/hooks/use-admin-properties";
import { useMarkRentPaid } from "@/lib/api/hooks/use-admin-actions";
import type { LeaseSimple } from "@/lib/schemas/admin";

export default function MarkPaidScreen() {
  const [selectedLease, setSelectedLease] = useState<LeaseSimple | null>(null);
  const [referenceMonth, setReferenceMonth] = useState("");
  const [amountPaid, setAmountPaid] = useState("");

  const { data: leases, isLoading } = useLeases({ is_active: true });
  const markPaid = useMarkRentPaid();

  function handleSelectLease(lease: LeaseSimple): void {
    setSelectedLease(lease);
    setAmountPaid(lease.rental_value);
  }

  function handleSubmit(): void {
    if (selectedLease === null) {
      Alert.alert("Erro", "Selecione uma locação.");
      return;
    }
    if (!referenceMonth) {
      Alert.alert("Erro", "Informe o mês de referência (YYYY-MM).");
      return;
    }
    if (!amountPaid) {
      Alert.alert("Erro", "Informe o valor pago.");
      return;
    }

    markPaid.mutate(
      {
        lease_id: selectedLease.id,
        reference_month: referenceMonth,
        amount_paid: amountPaid,
      },
      {
        onSuccess: () => {
          Alert.alert("Sucesso", "Pagamento registrado com sucesso.");
          setSelectedLease(null);
          setReferenceMonth("");
          setAmountPaid("");
        },
        onError: () => Alert.alert("Erro", "Não foi possível registrar o pagamento."),
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
                  onPress={() => handleSelectLease(lease)}
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
        <Card.Title title="Dados do Pagamento" />
        <Card.Content style={styles.formContent}>
          <TextInput
            label="Mês de referência (YYYY-MM)"
            value={referenceMonth}
            onChangeText={setReferenceMonth}
            mode="outlined"
            placeholder="2026-03"
            style={styles.input}
          />
          <TextInput
            label="Valor pago (R$)"
            value={amountPaid}
            onChangeText={setAmountPaid}
            mode="outlined"
            keyboardType="decimal-pad"
            style={styles.input}
          />
        </Card.Content>
      </Card>

      <Button
        mode="contained"
        onPress={handleSubmit}
        loading={markPaid.isPending}
        disabled={markPaid.isPending}
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
