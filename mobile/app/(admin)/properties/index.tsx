import { FlatList, StyleSheet, View } from "react-native";
import { Card, Text } from "react-native-paper";
import { useRouter } from "expo-router";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useBuildings } from "@/lib/api/hooks/use-admin-properties";
import type { Building } from "@/lib/schemas/admin";

function BuildingItem({ item }: { item: Building }) {
  const router = useRouter();
  return (
    <Card
      style={styles.card}
      onPress={() => router.push(`/(admin)/properties/${item.id}`)}
    >
      <Card.Content style={styles.cardContent}>
        <FontAwesome name="building" size={20} color="#555" style={styles.icon} />
        <View style={styles.info}>
          <Text variant="titleMedium">{item.name}</Text>
          <Text variant="bodySmall" style={styles.subText}>
            {item.address}
          </Text>
          <Text variant="bodySmall" style={styles.subText}>
            Nº {item.street_number}
          </Text>
        </View>
        <FontAwesome name="chevron-right" size={16} color="#bbb" />
      </Card.Content>
    </Card>
  );
}

export default function PropertiesListScreen() {
  const { data: buildings, isLoading } = useBuildings();

  if (isLoading) {
    return (
      <View style={styles.center}>
        <Text variant="bodyMedium">Carregando...</Text>
      </View>
    );
  }

  if (!buildings || buildings.length === 0) {
    return (
      <View style={styles.center}>
        <Text variant="bodyMedium" style={styles.subText}>
          Nenhum prédio cadastrado.
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={buildings}
      keyExtractor={(item) => String(item.id)}
      renderItem={({ item }) => <BuildingItem item={item} />}
      contentContainerStyle={styles.list}
    />
  );
}

const styles = StyleSheet.create({
  list: { padding: 16, gap: 12 },
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: 16 },
  card: { borderRadius: 8 },
  cardContent: { flexDirection: "row", alignItems: "center" },
  icon: { marginRight: 12 },
  info: { flex: 1 },
  subText: { color: "gray", marginTop: 2 },
});
