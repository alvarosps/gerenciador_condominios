import { FlatList, StyleSheet, View } from "react-native";
import { Button, Card, Divider, Text } from "react-native-paper";
import {
  useAdminNotifications,
  useMarkAdminNotificationRead,
  useMarkAllAdminNotificationsRead,
} from "@/lib/api/hooks/use-admin-notifications";
import type { TenantNotification } from "@/lib/schemas/tenant";

function NotificationItem({
  item,
  onMarkRead,
  isPending,
}: {
  item: TenantNotification;
  onMarkRead: (id: number) => void;
  isPending: boolean;
}) {
  const sentAt = new Date(item.sent_at).toLocaleDateString("pt-BR");

  return (
    <View style={[styles.notifContainer, !item.is_read && styles.unreadContainer]}>
      <View style={styles.notifHeader}>
        <Text variant="titleSmall" style={!item.is_read ? styles.unreadTitle : undefined}>
          {item.title}
        </Text>
        <Text variant="bodySmall" style={styles.dateText}>
          {sentAt}
        </Text>
      </View>
      <Text variant="bodyMedium" style={styles.bodyText}>
        {item.body}
      </Text>
      {!item.is_read && (
        <Button
          mode="text"
          compact
          onPress={() => onMarkRead(item.id)}
          disabled={isPending}
          style={styles.markReadButton}
        >
          Marcar como lida
        </Button>
      )}
      <Divider style={styles.divider} />
    </View>
  );
}

export default function AdminNotificationsScreen() {
  const { data: notifications, isLoading } = useAdminNotifications();
  const markRead = useMarkAdminNotificationRead();
  const markAllRead = useMarkAllAdminNotificationsRead();

  const unreadCount = notifications?.filter((n) => !n.is_read).length ?? 0;

  if (isLoading) {
    return (
      <View style={styles.center}>
        <Text variant="bodyMedium">Carregando...</Text>
      </View>
    );
  }

  if (!notifications || notifications.length === 0) {
    return (
      <View style={styles.center}>
        <Text variant="bodyMedium" style={styles.subText}>
          Nenhuma notificação.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {unreadCount > 0 && (
        <Card style={styles.headerCard}>
          <Card.Content style={styles.headerContent}>
            <Text variant="bodyMedium">
              {unreadCount} notificação{unreadCount !== 1 ? "ões" : ""} não lida{unreadCount !== 1 ? "s" : ""}
            </Text>
            <Button
              mode="outlined"
              compact
              onPress={() => markAllRead.mutate()}
              disabled={markAllRead.isPending}
            >
              Marcar todas
            </Button>
          </Card.Content>
        </Card>
      )}

      <FlatList
        data={notifications}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }: { item: TenantNotification }) => (
          <NotificationItem
            item={item}
            onMarkRead={(id) => markRead.mutate(id)}
            isPending={markRead.isPending}
          />
        )}
        contentContainerStyle={styles.list}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f5f5" },
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: 16 },
  headerCard: { margin: 16, borderRadius: 8 },
  headerContent: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  list: { paddingHorizontal: 16, paddingBottom: 16 },
  notifContainer: { paddingVertical: 12, backgroundColor: "white", marginBottom: 2, paddingHorizontal: 4 },
  unreadContainer: { backgroundColor: "#E8F5FD" },
  notifHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 },
  unreadTitle: { fontWeight: "700" },
  dateText: { color: "gray" },
  bodyText: { color: "#333" },
  markReadButton: { alignSelf: "flex-start", marginTop: 4 },
  subText: { color: "gray" },
  divider: { marginTop: 8 },
});
