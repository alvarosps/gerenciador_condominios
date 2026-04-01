import { Alert, FlatList, StyleSheet, View } from "react-native";
import { Button, Card, Chip, Text } from "react-native-paper";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useApartments, useGenerateContract, useLeases } from "@/lib/api/hooks/use-admin-properties";
import type { Apartment } from "@/lib/schemas/admin";

function ApartmentItem({
  item,
  tenantName,
  leaseId,
  onGenerateContract,
}: {
  item: Apartment;
  tenantName: string | null;
  leaseId: number | null;
  onGenerateContract: (id: number) => void;
}) {
  const router = useRouter();
  return (
    <Card style={styles.card}>
      <Card.Content>
        <View style={styles.headerRow}>
          <Text variant="titleMedium">Apto {item.number}</Text>
          <Chip
            compact
            style={item.is_rented ? styles.rentedChip : styles.vacantChip}
            textStyle={item.is_rented ? styles.rentedText : styles.vacantText}
          >
            {item.is_rented ? "Alugado" : "Vago"}
          </Chip>
        </View>
        <Text variant="bodyMedium" style={styles.subText}>
          R$ {parseFloat(item.rental_value).toFixed(2).replace(".", ",")} / mês
        </Text>
        {tenantName !== null && (
          <Text variant="bodySmall" style={styles.subText}>
            Inquilino: {tenantName}
          </Text>
        )}
      </Card.Content>
      <Card.Actions>
        {leaseId !== null && (
          <Button mode="outlined" compact onPress={() => onGenerateContract(leaseId)}>
            Gerar Contrato
          </Button>
        )}
        {!item.is_rented && (
          <Button
            mode="contained"
            compact
            onPress={() =>
              router.push({
                pathname: "/(admin)/properties/new-lease",
                params: { apartmentId: item.id, apartmentNumber: item.number },
              })
            }
          >
            Nova Locação
          </Button>
        )}
      </Card.Actions>
    </Card>
  );
}

export default function BuildingDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const buildingId = parseInt(id, 10);
  const { data: apartments, isLoading: loadingApts } = useApartments(buildingId);
  const { data: leases, isLoading: loadingLeases } = useLeases({ building_id: buildingId });
  const generateContract = useGenerateContract();

  function handleGenerateContract(leaseId: number): void {
    Alert.alert("Gerar Contrato", "Deseja gerar o contrato PDF para esta locação?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Gerar",
        onPress: () => {
          generateContract.mutate(leaseId, {
            onSuccess: () => Alert.alert("Sucesso", "Contrato gerado com sucesso."),
            onError: () => Alert.alert("Erro", "Não foi possível gerar o contrato."),
          });
        },
      },
    ]);
  }

  const isLoading = loadingApts || loadingLeases;

  if (isLoading) {
    return (
      <View style={styles.center}>
        <Text variant="bodyMedium">Carregando...</Text>
      </View>
    );
  }

  function getTenantName(apartmentId: number): string | null {
    const lease = leases?.find((l) => l.apartment === apartmentId);
    return lease?.responsible_tenant.name ?? null;
  }

  function getLeaseId(apartmentId: number): number | null {
    const lease = leases?.find((l) => l.apartment === apartmentId);
    return lease?.id ?? null;
  }

  return (
    <FlatList
      data={apartments}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => (
        <ApartmentItem
          item={item}
          tenantName={getTenantName(item.id)}
          leaseId={getLeaseId(item.id)}
          onGenerateContract={handleGenerateContract}
        />
      )}
      contentContainerStyle={styles.list}
      ListEmptyComponent={
        <View style={styles.center}>
          <Text variant="bodyMedium" style={styles.subText}>
            Nenhum apartamento cadastrado.
          </Text>
        </View>
      }
    />
  );
}

const styles = StyleSheet.create({
  list: { padding: 16, gap: 12 },
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: 16 },
  card: { borderRadius: 8 },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  rentedChip: { backgroundColor: "#E8F5E9" },
  vacantChip: { backgroundColor: "#FFF3E0" },
  rentedText: { color: "#2E7D32" },
  vacantText: { color: "#E65100" },
  subText: { color: "gray", marginTop: 4 },
});
