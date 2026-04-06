import { Alert, ScrollView, StyleSheet, View } from "react-native";
import { Button, Card, Text, TextInput } from "react-native-paper";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { useApartments, useCreateLease, useTenantSearch } from "@/lib/api/hooks/use-admin-properties";
import type { TenantSearchResult } from "@/lib/schemas/admin";

export default function NewLeaseScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ apartmentId?: string; apartmentNumber?: string }>();

  const [selectedApartmentId, setSelectedApartmentId] = useState<number | null>(
    params.apartmentId !== undefined ? parseInt(params.apartmentId, 10) : null,
  );
  const [tenantSearch, setTenantSearch] = useState("");
  const [selectedTenant, setSelectedTenant] = useState<TenantSearchResult | null>(null);
  const [startDate, setStartDate] = useState("");
  const [validityMonths, setValidityMonths] = useState("12");
  const [rentalValue, setRentalValue] = useState("");

  const { data: apartments } = useApartments();
  const { data: searchResults } = useTenantSearch(tenantSearch);
  const createLease = useCreateLease();

  const availableApartments = apartments?.filter((a) => !a.is_rented) ?? [];

  function handleSelectApartment(id: number): void {
    setSelectedApartmentId(id);
    const apt = availableApartments.find((a) => a.id === id);
    if (apt) {
      setRentalValue(apt.rental_value);
    }
  }

  function handleSelectTenant(tenant: TenantSearchResult): void {
    setSelectedTenant(tenant);
    setTenantSearch(tenant.name);
  }

  function handleSubmit(): void {
    if (selectedApartmentId === null) {
      Alert.alert("Erro", "Selecione um apartamento.");
      return;
    }
    if (selectedTenant === null) {
      Alert.alert("Erro", "Selecione um inquilino.");
      return;
    }
    if (!startDate) {
      Alert.alert("Erro", "Informe a data de início (YYYY-MM-DD).");
      return;
    }
    if (!rentalValue) {
      Alert.alert("Erro", "Informe o valor do aluguel.");
      return;
    }

    createLease.mutate(
      {
        apartment: selectedApartmentId,
        responsible_tenant_id: selectedTenant.id,
        start_date: startDate,
        validity_months: parseInt(validityMonths, 10),
        rental_value: rentalValue,
        number_of_tenants: 1,
      },
      {
        onSuccess: () => {
          Alert.alert("Sucesso", "Locação criada com sucesso.", [
            { text: "OK", onPress: () => router.back() },
          ]);
        },
        onError: () => {
          Alert.alert("Erro", "Não foi possível criar a locação.");
        },
      },
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Card style={styles.card}>
        <Card.Title title="Apartamento" />
        <Card.Content style={styles.content}>
          {params.apartmentId !== undefined ? (
            <Text variant="bodyMedium">Apto {params.apartmentNumber}</Text>
          ) : (
            <>
              <Text variant="bodySmall" style={styles.label}>
                Selecionar apartamento disponível:
              </Text>
              <View style={styles.optionList}>
                {availableApartments.map((apt) => (
                  <Button
                    key={apt.id}
                    mode={selectedApartmentId === apt.id ? "contained" : "outlined"}
                    compact
                    style={styles.optionButton}
                    onPress={() => handleSelectApartment(apt.id)}
                  >
                    Apto {apt.number}
                  </Button>
                ))}
                {availableApartments.length === 0 && (
                  <Text variant="bodySmall" style={styles.subText}>
                    Nenhum apartamento disponível.
                  </Text>
                )}
              </View>
            </>
          )}
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Title title="Inquilino" />
        <Card.Content style={styles.content}>
          <TextInput
            label="Buscar inquilino"
            value={tenantSearch}
            onChangeText={(text) => {
              setTenantSearch(text);
              setSelectedTenant(null);
            }}
            mode="outlined"
            style={styles.input}
          />
          {searchResults && searchResults.length > 0 && selectedTenant === null && (
            <View style={styles.searchResults}>
              {searchResults.map((t) => (
                <Button
                  key={t.id}
                  mode="text"
                  compact
                  onPress={() => handleSelectTenant(t)}
                  style={styles.searchResultItem}
                >
                  {t.name} — {t.cpf_cnpj}
                </Button>
              ))}
            </View>
          )}
          {selectedTenant !== null && (
            <Text variant="bodySmall" style={styles.selectedLabel}>
              Selecionado: {selectedTenant.name}
            </Text>
          )}
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Title title="Dados da Locação" />
        <Card.Content style={styles.content}>
          <TextInput
            label="Data de início (YYYY-MM-DD)"
            value={startDate}
            onChangeText={setStartDate}
            mode="outlined"
            style={styles.input}
            placeholder="2026-01-01"
          />
          <TextInput
            label="Prazo (meses)"
            value={validityMonths}
            onChangeText={setValidityMonths}
            mode="outlined"
            keyboardType="numeric"
            style={styles.input}
          />
          <TextInput
            label="Valor do aluguel (R$)"
            value={rentalValue}
            onChangeText={setRentalValue}
            mode="outlined"
            keyboardType="decimal-pad"
            style={styles.input}
          />
        </Card.Content>
      </Card>

      <Button
        mode="contained"
        onPress={handleSubmit}
        loading={createLease.isPending}
        disabled={createLease.isPending}
        style={styles.submitButton}
      >
        Criar Locação
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  card: { borderRadius: 8 },
  content: { gap: 8 },
  label: { color: "gray", marginBottom: 4 },
  input: { backgroundColor: "white" },
  optionList: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  optionButton: { marginBottom: 4 },
  searchResults: { borderWidth: 1, borderColor: "#ddd", borderRadius: 4, marginTop: 4 },
  searchResultItem: { justifyContent: "flex-start" },
  selectedLabel: { color: "#2E7D32", marginTop: 4 },
  subText: { color: "gray" },
  submitButton: { marginTop: 8 },
});
