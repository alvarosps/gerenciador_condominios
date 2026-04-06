import { Alert, ScrollView, StyleSheet } from "react-native";
import { Button, Card, Text, TextInput } from "react-native-paper";
import { useState } from "react";
import { useTenantMe } from "@/lib/api/hooks/use-tenant";
import { useSimulateDueDate } from "@/lib/api/hooks/use-tenant-simulate";
import type { SimulateDueDate } from "@/lib/schemas/tenant";

export default function SimulateScreen() {
  const { data: tenant } = useTenantMe();
  const simulateMutation = useSimulateDueDate();

  const [newDueDay, setNewDueDay] = useState("");
  const [result, setResult] = useState<SimulateDueDate | null>(null);

  async function handleSimulate(): Promise<void> {
    const day = parseInt(newDueDay, 10);
    if (isNaN(day) || day < 1 || day > 31) {
      Alert.alert("Erro", "Informe um dia válido entre 1 e 31.");
      return;
    }
    try {
      const data = await simulateMutation.mutateAsync({ new_due_day: day });
      setResult(data);
    } catch {
      Alert.alert("Erro", "Não foi possível simular a troca de vencimento.");
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={styles.cardTitle}>
            Vencimento Atual
          </Text>
          <Text variant="headlineSmall">Dia {tenant?.due_day ?? "—"}</Text>
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={styles.cardTitle}>
            Simular Novo Vencimento
          </Text>
          <TextInput
            label="Novo dia de vencimento (1-31)"
            value={newDueDay}
            onChangeText={setNewDueDay}
            keyboardType="numeric"
            mode="outlined"
            style={styles.input}
          />
          <Button
            mode="contained"
            onPress={() => void handleSimulate()}
            loading={simulateMutation.isPending}
            disabled={simulateMutation.isPending}
          >
            Simular
          </Button>
        </Card.Content>
      </Card>

      {result !== null && (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="titleMedium" style={styles.cardTitle}>
              Resultado da Simulação
            </Text>
            <Text variant="bodyMedium">
              Dias de diferença:{" "}
              <Text style={styles.highlight}>{result.days_difference}</Text>
            </Text>
            <Text variant="bodyMedium">
              Taxa diária: R${" "}
              <Text style={styles.highlight}>
                {parseFloat(result.daily_rate).toFixed(2).replace(".", ",")}
              </Text>
            </Text>
            <Text variant="bodyMedium">
              Taxa total: R${" "}
              <Text style={styles.highlight}>
                {parseFloat(result.fee).toFixed(2).replace(".", ",")}
              </Text>
            </Text>
          </Card.Content>
        </Card>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 16 },
  card: { borderRadius: 8 },
  cardTitle: { marginBottom: 8 },
  input: { marginBottom: 12 },
  highlight: { fontWeight: "700" },
});
