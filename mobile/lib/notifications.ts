import { useEffect, useRef } from "react";
import { Platform } from "react-native";
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { useRouter } from "expo-router";
import { apiClient } from "@/lib/api/client";

// Configure notification handler
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export async function registerForPushNotifications(): Promise<string | null> {
  if (!Device.isDevice) {
    console.warn("Push notifications require a physical device");
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    return null;
  }

  const tokenData = await Notifications.getExpoPushTokenAsync();
  const token = tokenData.data;

  // Register token with backend
  try {
    await apiClient.post("/devices/register/", {
      token,
      platform: Platform.OS,
    });
  } catch (error) {
    console.error("Failed to register push token:", error);
  }

  return token;
}

export async function unregisterPushToken(): Promise<void> {
  try {
    const tokenData = await Notifications.getExpoPushTokenAsync();
    await apiClient.post("/devices/unregister/", {
      token: tokenData.data,
    });
  } catch {
    // Best effort — token cleanup on logout
  }
}

export function useNotificationDeepLinking(): void {
  const router = useRouter();
  const responseListener = useRef<Notifications.Subscription | null>(null);

  useEffect(() => {
    // Handle notification tapped when app is open
    responseListener.current = Notifications.addNotificationResponseReceivedListener(
      (response) => {
        const data = response.notification.request.content.data as Record<string, unknown>;
        const screen = data.screen as string | undefined;

        if (screen === "payments") {
          router.push("/(tenant)/payments");
        } else if (screen === "proofs") {
          router.push("/(admin)/actions/proofs");
        } else if (screen === "properties") {
          router.push("/(admin)/properties");
        }
      },
    );

    return () => {
      if (responseListener.current) {
        Notifications.removeNotificationSubscription(responseListener.current);
      }
    };
  }, [router]);
}
