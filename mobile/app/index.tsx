import { Redirect } from "expo-router";
import { useAuthStore } from "@/store/auth-store";
import { LoadingScreen } from "@/components/ui/loading-screen";

export default function Index() {
  const { isAuthenticated, isLoading, role } = useAuthStore();

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Redirect href="/login" />;
  }

  if (role === "admin") {
    return <Redirect href="/(admin)" />;
  }

  return <Redirect href="/(tenant)" />;
}
