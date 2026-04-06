import { useEffect } from "react";
import { Stack } from "expo-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { PaperProvider } from "react-native-paper";
import { queryClient } from "@/lib/query-client";
import { useAuthStore } from "@/store/auth-store";
import { LoadingScreen } from "@/components/ui/loading-screen";
import {
  registerForPushNotifications,
  useNotificationDeepLinking,
} from "@/lib/notifications";

export default function RootLayout() {
  const { isLoading, hydrateFromStorage } = useAuthStore();

  useEffect(() => {
    void hydrateFromStorage();
  }, [hydrateFromStorage]);

  const { isAuthenticated } = useAuthStore();
  useEffect(() => {
    if (isAuthenticated) {
      void registerForPushNotifications();
    }
  }, [isAuthenticated]);

  useNotificationDeepLinking();

  if (isLoading) {
    return (
      <PaperProvider>
        <LoadingScreen />
      </PaperProvider>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <PaperProvider>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="login" />
          <Stack.Screen name="(tenant)" />
          <Stack.Screen name="(admin)" />
        </Stack>
      </PaperProvider>
    </QueryClientProvider>
  );
}
