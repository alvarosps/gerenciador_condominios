import { Alert, ScrollView, StyleSheet, View } from "react-native";
import { Button, Card, Text, TextInput } from "react-native-paper";
import { useState } from "react";
import * as Clipboard from "expo-clipboard";
import * as ImagePicker from "expo-image-picker";
import * as DocumentPicker from "expo-document-picker";
import QRCode from "react-native-qrcode-svg";
import { useRouter } from "expo-router";
import { useTenantMe } from "@/lib/api/hooks/use-tenant";
import { useGeneratePix } from "@/lib/api/hooks/use-tenant-pix";
import { useUploadProof } from "@/lib/api/hooks/use-tenant-proof";
import type { PixPayload } from "@/lib/schemas/tenant";

export default function PixScreen() {
  const router = useRouter();
  const { data: tenant } = useTenantMe();
  const generatePix = useGeneratePix();
  const uploadProof = useUploadProof();

  const [pixPayload, setPixPayload] = useState<PixPayload | null>(null);
  const [referenceMonth, setReferenceMonth] = useState("");
  const [uploading, setUploading] = useState(false);

  async function handleGeneratePix(): Promise<void> {
    try {
      const result = await generatePix.mutateAsync();
      setPixPayload(result);
    } catch {
      Alert.alert("Erro", "Não foi possível gerar o PIX. Tente novamente.");
    }
  }

  async function handleCopyPix(): Promise<void> {
    if (!pixPayload) return;
    await Clipboard.setStringAsync(pixPayload.payload);
    Alert.alert("Copiado", "Código PIX copiado para a área de transferência.");
  }

  async function handleUploadPhoto(): Promise<void> {
    if (!referenceMonth) {
      Alert.alert("Atenção", "Informe o mês de referência antes de enviar o comprovante.");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsEditing: false,
      quality: 0.8,
    });
    if (result.canceled || !result.assets[0]) return;
    const asset = result.assets[0];
    const fileName = asset.fileName ?? "proof.jpg";
    const mimeType = asset.mimeType ?? "image/jpeg";
    await submitProof({ uri: asset.uri, name: fileName, type: mimeType });
  }

  async function handleUploadPdf(): Promise<void> {
    if (!referenceMonth) {
      Alert.alert("Atenção", "Informe o mês de referência antes de enviar o comprovante.");
      return;
    }
    const result = await DocumentPicker.getDocumentAsync({
      type: "application/pdf",
      copyToCacheDirectory: true,
    });
    if (result.canceled || !result.assets[0]) return;
    const asset = result.assets[0];
    await submitProof({
      uri: asset.uri,
      name: asset.name,
      type: "application/pdf",
    });
  }

  async function submitProof(file: { uri: string; name: string; type: string }): Promise<void> {
    setUploading(true);
    try {
      await uploadProof.mutateAsync({
        reference_month: referenceMonth,
        file,
        pix_code: pixPayload?.payload,
      });
      Alert.alert("Sucesso", "Comprovante enviado com sucesso!", [
        { text: "OK", onPress: () => router.back() },
      ]);
    } catch {
      Alert.alert("Erro", "Não foi possível enviar o comprovante. Tente novamente.");
    } finally {
      setUploading(false);
    }
  }

  const rentalValue = tenant?.lease?.rental_value
    ? `R$ ${parseFloat(tenant.lease.rental_value).toFixed(2).replace(".", ",")}`
    : "—";

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={styles.cardTitle}>
            Valor do Aluguel
          </Text>
          <Text variant="headlineSmall">{rentalValue}</Text>
        </Card.Content>
      </Card>

      {!pixPayload ? (
        <Button
          mode="contained"
          onPress={() => void handleGeneratePix()}
          loading={generatePix.isPending}
          disabled={generatePix.isPending}
          style={styles.button}
        >
          Gerar PIX
        </Button>
      ) : (
        <Card style={styles.card}>
          <Card.Content style={styles.qrContainer}>
            <Text variant="titleMedium" style={styles.cardTitle}>
              QR Code PIX
            </Text>
            <View style={styles.qrWrapper}>
              <QRCode value={pixPayload.payload} size={200} />
            </View>
            <Text variant="bodySmall" style={styles.merchantText}>
              {pixPayload.merchant_name}
            </Text>
            <Button
              mode="outlined"
              onPress={() => void handleCopyPix()}
              style={styles.copyButton}
            >
              Copiar código PIX
            </Button>
          </Card.Content>
        </Card>
      )}

      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={styles.cardTitle}>
            Enviar Comprovante
          </Text>
          <TextInput
            label="Mês de referência (AAAA-MM-DD)"
            value={referenceMonth}
            onChangeText={setReferenceMonth}
            mode="outlined"
            placeholder="Ex: 2026-04-01"
            style={styles.input}
          />
          <View style={styles.uploadRow}>
            <Button
              mode="outlined"
              onPress={() => void handleUploadPhoto()}
              loading={uploading}
              disabled={uploading}
              style={styles.uploadButton}
            >
              Foto
            </Button>
            <Button
              mode="outlined"
              onPress={() => void handleUploadPdf()}
              loading={uploading}
              disabled={uploading}
              style={styles.uploadButton}
            >
              PDF
            </Button>
          </View>
        </Card.Content>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 16 },
  card: { borderRadius: 8 },
  cardTitle: { marginBottom: 8 },
  button: { marginTop: 8 },
  qrContainer: { alignItems: "center" },
  qrWrapper: { marginVertical: 16 },
  merchantText: { color: "gray", marginBottom: 8 },
  copyButton: { alignSelf: "stretch" },
  input: { marginBottom: 12 },
  uploadRow: { flexDirection: "row", gap: 12 },
  uploadButton: { flex: 1 },
});
