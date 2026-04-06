import { ScrollView, StyleSheet } from "react-native";
import { Card, Text } from "react-native-paper";
import { useRouter } from "expo-router";
import FontAwesome from "@expo/vector-icons/FontAwesome";

export default function ActionsMenuScreen() {
  const router = useRouter();

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text variant="headlineSmall" style={styles.heading}>
        Ações Administrativas
      </Text>

      <Card style={styles.card} onPress={() => router.push("/(admin)/actions/mark-paid")}>
        <Card.Content style={styles.cardContent}>
          <FontAwesome name="check-circle" size={28} color="#2E7D32" style={styles.icon} />
          <Text variant="titleMedium" style={styles.cardTitle}>
            Marcar Aluguel Pago
          </Text>
          <Text variant="bodySmall" style={styles.subText}>
            Registrar pagamento de aluguel manualmente
          </Text>
        </Card.Content>
      </Card>

      <Card style={styles.card} onPress={() => router.push("/(admin)/actions/proofs")}>
        <Card.Content style={styles.cardContent}>
          <FontAwesome name="file-image-o" size={28} color="#1565C0" style={styles.icon} />
          <Text variant="titleMedium" style={styles.cardTitle}>
            Aprovar Comprovantes
          </Text>
          <Text variant="bodySmall" style={styles.subText}>
            Revisar comprovantes enviados pelos inquilinos
          </Text>
        </Card.Content>
      </Card>

      <Card style={styles.card} onPress={() => router.push("/(admin)/actions/rent-adjustment")}>
        <Card.Content style={styles.cardContent}>
          <FontAwesome name="line-chart" size={28} color="#E65100" style={styles.icon} />
          <Text variant="titleMedium" style={styles.cardTitle}>
            Aplicar Reajuste
          </Text>
          <Text variant="bodySmall" style={styles.subText}>
            Aplicar reajuste de aluguel em locações elegíveis
          </Text>
        </Card.Content>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 12 },
  heading: { marginBottom: 4 },
  card: { borderRadius: 8 },
  cardContent: { gap: 4 },
  icon: { marginBottom: 8 },
  cardTitle: { fontWeight: "600" },
  subText: { color: "gray" },
});
