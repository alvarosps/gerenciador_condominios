import { Alert, ScrollView, StyleSheet } from "react-native";
import { Button, Card, Text } from "react-native-paper";
import { useState } from "react";
import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";
import { useTenantMe } from "@/lib/api/hooks/use-tenant";
import { useAuthStore } from "@/store/auth-store";
import { getAccessToken } from "@/lib/secure-store";

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8008/api";

export default function ContractScreen() {
  const { data: tenant, isLoading } = useTenantMe();
  const { user } = useAuthStore();
  const [downloading, setDownloading] = useState(false);

  async function handleDownloadContract(): Promise<void> {
    setDownloading(true);
    try {
      const token = await getAccessToken();
      const downloadResult = await FileSystem.downloadAsync(
        `${API_BASE_URL}/tenant/contract/`,
        `${FileSystem.cacheDirectory}contrato.pdf`,
        {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        },
      );

      const isSharingAvailable = await Sharing.isAvailableAsync();
      if (!isSharingAvailable) {
        Alert.alert("Erro", "Compartilhamento não disponível neste dispositivo.");
        return;
      }

      await Sharing.shareAsync(downloadResult.uri, {
        mimeType: "application/pdf",
        dialogTitle: "Contrato de Locação",
      });
    } catch {
      Alert.alert("Erro", "Não foi possível baixar o contrato. Tente novamente.");
    } finally {
      setDownloading(false);
    }
  }

  if (isLoading) {
    return (
      <ScrollView contentContainerStyle={styles.container}>
        <Text variant="bodyMedium">Carregando...</Text>
      </ScrollView>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {tenant?.apartment ? (
        <Card style={styles.card}>
          <Card.Title title="Imóvel" />
          <Card.Content>
            <Text variant="bodyMedium">
              <Text style={styles.label}>Apartamento: </Text>
              {tenant.apartment.number}
            </Text>
            <Text variant="bodyMedium">
              <Text style={styles.label}>Condomínio: </Text>
              {tenant.apartment.building_name}
            </Text>
            <Text variant="bodyMedium">
              <Text style={styles.label}>Endereço: </Text>
              {tenant.apartment.building_address}
            </Text>
          </Card.Content>
        </Card>
      ) : (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="bodyMedium" style={styles.emptyText}>
              Nenhum imóvel associado.
            </Text>
          </Card.Content>
        </Card>
      )}

      {tenant?.lease ? (
        <Card style={styles.card}>
          <Card.Title title="Contrato" />
          <Card.Content>
            <Text variant="bodyMedium">
              <Text style={styles.label}>Início: </Text>
              {new Date(tenant.lease.start_date + "T12:00:00").toLocaleDateString("pt-BR")}
            </Text>
            <Text variant="bodyMedium">
              <Text style={styles.label}>Duração: </Text>
              {tenant.lease.validity_months} meses
            </Text>
            <Text variant="bodyMedium">
              <Text style={styles.label}>Aluguel: </Text>
              R$ {parseFloat(tenant.lease.rental_value).toFixed(2).replace(".", ",")}
            </Text>
            {tenant.lease.pending_rental_value !== null && (
              <Text variant="bodyMedium">
                <Text style={styles.label}>Valor pendente: </Text>
                R${" "}
                {parseFloat(tenant.lease.pending_rental_value).toFixed(2).replace(".", ",")}
              </Text>
            )}
            <Text variant="bodyMedium">
              <Text style={styles.label}>Ocupantes: </Text>
              {tenant.lease.number_of_tenants}
            </Text>
          </Card.Content>
          <Card.Actions>
            {tenant.lease.contract_generated ? (
              <Button
                mode="contained"
                onPress={() => void handleDownloadContract()}
                loading={downloading}
                disabled={downloading}
              >
                Ver Contrato (PDF)
              </Button>
            ) : (
              <Text variant="bodySmall" style={styles.emptyText}>
                Contrato ainda não gerado.
              </Text>
            )}
          </Card.Actions>
        </Card>
      ) : (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="bodyMedium" style={styles.emptyText}>
              Nenhum contrato ativo.
            </Text>
          </Card.Content>
        </Card>
      )}

      <Card style={styles.card}>
        <Card.Title title="Inquilino Responsável" />
        <Card.Content>
          <Text variant="bodyMedium">
            <Text style={styles.label}>Nome: </Text>
            {user?.name ?? "—"}
          </Text>
        </Card.Content>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 16 },
  card: { borderRadius: 8 },
  label: { fontWeight: "600" },
  emptyText: { color: "gray" },
});
