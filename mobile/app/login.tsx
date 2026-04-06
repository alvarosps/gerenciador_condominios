import { useState } from "react";
import { Alert, KeyboardAvoidingView, Platform, StyleSheet, View } from "react-native";
import { Button, SegmentedButtons, Text, TextInput } from "react-native-paper";
import { apiClient } from "@/lib/api/client";
import { useAuthStore } from "@/store/auth-store";

type LoginMode = "admin" | "tenant";

interface TokenResponse {
  access: string;
  refresh: string;
}

interface UserMeResponse {
  id: number;
  first_name: string;
  last_name: string;
  is_staff: boolean;
}

interface TenantMeResponse {
  id: number;
  name: string;
}

export default function LoginScreen() {
  const { setAuth } = useAuthStore();
  const [mode, setMode] = useState<LoginMode>("tenant");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [cpfCnpj, setCpfCnpj] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleAdminLogin(): Promise<void> {
    if (!username || !password) {
      Alert.alert("Erro", "Preencha todos os campos.");
      return;
    }
    setLoading(true);
    try {
      const tokenRes = await apiClient.post<TokenResponse>("/auth/token/", { username, password });
      const userRes = await apiClient.get<UserMeResponse>("/auth/me/", {
        headers: { Authorization: `Bearer ${tokenRes.data.access}` },
      });
      await setAuth(
        {
          id: userRes.data.id,
          name: `${userRes.data.first_name} ${userRes.data.last_name}`.trim(),
          is_staff: userRes.data.is_staff,
        },
        tokenRes.data.access,
        tokenRes.data.refresh,
      );
    } catch {
      Alert.alert("Erro", "Credenciais inválidas.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRequestCode(): Promise<void> {
    if (!cpfCnpj) {
      Alert.alert("Erro", "Digite seu CPF ou CNPJ.");
      return;
    }
    setLoading(true);
    try {
      await apiClient.post("/auth/whatsapp/request/", { cpf_cnpj: cpfCnpj });
      setCodeSent(true);
      Alert.alert("Código enviado", "Verifique seu WhatsApp.");
    } catch {
      Alert.alert("Erro", "CPF/CNPJ não encontrado ou muitas tentativas.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyCode(): Promise<void> {
    if (!code) {
      Alert.alert("Erro", "Digite o código de verificação.");
      return;
    }
    setLoading(true);
    try {
      const res = await apiClient.post<TokenResponse>("/auth/whatsapp/verify/", {
        cpf_cnpj: cpfCnpj,
        code,
      });
      const meRes = await apiClient.get<TenantMeResponse>("/tenant/me/", {
        headers: { Authorization: `Bearer ${res.data.access}` },
      });
      await setAuth(
        { id: meRes.data.id, name: meRes.data.name, is_staff: false },
        res.data.access,
        res.data.refresh,
      );
    } catch {
      Alert.alert("Erro", "Código inválido ou expirado.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.inner}>
        <Text variant="headlineMedium" style={styles.title}>
          Condominios Manager
        </Text>
        <SegmentedButtons
          value={mode}
          onValueChange={(v) => {
            setMode(v as LoginMode);
            setCodeSent(false);
          }}
          buttons={[
            { value: "tenant", label: "Inquilino" },
            { value: "admin", label: "Administrador" },
          ]}
          style={styles.segmented}
        />
        {mode === "admin" ? (
          <View style={styles.form}>
            <TextInput
              label="Usuário"
              value={username}
              onChangeText={setUsername}
              autoCapitalize="none"
              mode="outlined"
              style={styles.input}
            />
            <TextInput
              label="Senha"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              mode="outlined"
              style={styles.input}
            />
            <Button
              mode="contained"
              onPress={() => void handleAdminLogin()}
              loading={loading}
              disabled={loading}
              style={styles.button}
            >
              Entrar
            </Button>
          </View>
        ) : (
          <View style={styles.form}>
            <TextInput
              label="CPF ou CNPJ"
              value={cpfCnpj}
              onChangeText={setCpfCnpj}
              keyboardType="numeric"
              mode="outlined"
              style={styles.input}
              disabled={codeSent}
            />
            {codeSent ? (
              <>
                <TextInput
                  label="Código de verificação"
                  value={code}
                  onChangeText={setCode}
                  keyboardType="numeric"
                  maxLength={6}
                  mode="outlined"
                  style={styles.input}
                />
                <Button
                  mode="contained"
                  onPress={() => void handleVerifyCode()}
                  loading={loading}
                  disabled={loading}
                  style={styles.button}
                >
                  Verificar
                </Button>
                <Button
                  mode="text"
                  onPress={() => {
                    setCodeSent(false);
                    setCode("");
                  }}
                  style={styles.button}
                >
                  Reenviar código
                </Button>
              </>
            ) : (
              <Button
                mode="contained"
                onPress={() => void handleRequestCode()}
                loading={loading}
                disabled={loading}
                style={styles.button}
              >
                Enviar código via WhatsApp
              </Button>
            )}
          </View>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  inner: { flex: 1, justifyContent: "center", padding: 24 },
  title: { textAlign: "center", marginBottom: 32 },
  segmented: { marginBottom: 24 },
  form: { gap: 12 },
  input: { marginBottom: 4 },
  button: { marginTop: 8 },
});
