import { FlatList, StyleSheet, View } from "react-native";
import { Alert } from "react-native";
import { Button, Card, Chip, Divider, Text, TextInput } from "react-native-paper";
import { useState } from "react";
import { useAdminProofs, useReviewProof } from "@/lib/api/hooks/use-admin-actions";
import type { PaymentProofAdmin } from "@/lib/schemas/admin";

function ProofItem({
  item,
  onApprove,
  onReject,
  isPending,
}: {
  item: PaymentProofAdmin;
  onApprove: (id: number) => void;
  onReject: (id: number, reason: string) => void;
  isPending: boolean;
}) {
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");

  const date = new Date(item.created_at).toLocaleDateString("pt-BR");

  function handleRejectConfirm(): void {
    if (!rejectionReason.trim()) {
      Alert.alert("Erro", "Informe o motivo da rejeição.");
      return;
    }
    onReject(item.id, rejectionReason);
    setShowRejectInput(false);
    setRejectionReason("");
  }

  return (
    <View style={styles.itemContainer}>
      <View style={styles.itemHeader}>
        <View style={styles.itemInfo}>
          <Text variant="titleSmall">{item.tenant_name}</Text>
          <Text variant="bodySmall" style={styles.subText}>
            Apto {item.apartment_number} — {item.reference_month}
          </Text>
          <Text variant="bodySmall" style={styles.subText}>
            Enviado em {date}
          </Text>
        </View>
        <Chip compact style={styles.pendingChip} textStyle={styles.pendingText}>
          Pendente
        </Chip>
      </View>

      {showRejectInput ? (
        <View style={styles.rejectContainer}>
          <TextInput
            label="Motivo da rejeição"
            value={rejectionReason}
            onChangeText={setRejectionReason}
            mode="outlined"
            style={styles.rejectInput}
            multiline
          />
          <View style={styles.rejectActions}>
            <Button
              mode="outlined"
              compact
              onPress={() => {
                setShowRejectInput(false);
                setRejectionReason("");
              }}
            >
              Cancelar
            </Button>
            <Button
              mode="contained"
              compact
              buttonColor="#C62828"
              onPress={handleRejectConfirm}
              disabled={isPending}
            >
              Confirmar Rejeição
            </Button>
          </View>
        </View>
      ) : (
        <View style={styles.actionRow}>
          <Button
            mode="contained"
            compact
            buttonColor="#2E7D32"
            onPress={() => onApprove(item.id)}
            disabled={isPending}
          >
            Aprovar
          </Button>
          <Button
            mode="outlined"
            compact
            textColor="#C62828"
            style={styles.rejectButton}
            onPress={() => setShowRejectInput(true)}
            disabled={isPending}
          >
            Rejeitar
          </Button>
        </View>
      )}
      <Divider style={styles.divider} />
    </View>
  );
}

export default function ProofsScreen() {
  const { data: proofs, isLoading } = useAdminProofs("pending");
  const reviewProof = useReviewProof();

  function handleApprove(id: number): void {
    reviewProof.mutate(
      { id, action: "approve" },
      {
        onSuccess: () => Alert.alert("Sucesso", "Comprovante aprovado."),
        onError: () => Alert.alert("Erro", "Não foi possível aprovar o comprovante."),
      },
    );
  }

  function handleReject(id: number, reason: string): void {
    reviewProof.mutate(
      { id, action: "reject", reason },
      {
        onSuccess: () => Alert.alert("Sucesso", "Comprovante rejeitado."),
        onError: () => Alert.alert("Erro", "Não foi possível rejeitar o comprovante."),
      },
    );
  }

  if (isLoading) {
    return (
      <View style={styles.center}>
        <Text variant="bodyMedium">Carregando...</Text>
      </View>
    );
  }

  if (!proofs || proofs.length === 0) {
    return (
      <View style={styles.center}>
        <Text variant="bodyMedium" style={styles.subText}>
          Nenhum comprovante pendente.
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={proofs}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }: { item: PaymentProofAdmin }) => (
        <ProofItem
          item={item}
          onApprove={handleApprove}
          onReject={handleReject}
          isPending={reviewProof.isPending}
        />
      )}
      contentContainerStyle={styles.list}
    />
  );
}

const styles = StyleSheet.create({
  list: { padding: 16 },
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: 16 },
  itemContainer: { marginBottom: 8 },
  itemHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 },
  itemInfo: { flex: 1 },
  subText: { color: "gray", marginTop: 2 },
  pendingChip: { backgroundColor: "#FFF8E1" },
  pendingText: { color: "#E65100" },
  actionRow: { flexDirection: "row", gap: 8, marginBottom: 8 },
  rejectButton: { borderColor: "#C62828" },
  rejectContainer: { gap: 8, marginBottom: 8 },
  rejectInput: { backgroundColor: "white" },
  rejectActions: { flexDirection: "row", gap: 8, justifyContent: "flex-end" },
  divider: { marginTop: 8 },
});
