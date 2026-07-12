'use client';

import { FileText, Download, Loader2, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useDownloadContract } from '@/lib/api/hooks/use-tenant-notifications';
import { useTenantProfile } from '@/lib/api/hooks/use-tenant-portal';
import { getErrorMessage } from '@/lib/utils/error-handler';

export default function TenantContractPage() {
  const downloadContract = useDownloadContract();
  const { data: profile, isLoading, isError } = useTenantProfile();

  const handleDownload = async () => {
    try {
      await downloadContract.mutateAsync();
      toast.success('Download do contrato iniciado!');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Erro ao baixar contrato'));
    }
  };

  const contractGenerated = profile?.lease?.contract_generated ?? false;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FileText className="h-6 w-6" />
          Meu Contrato
        </h1>
        <p className="text-muted-foreground mt-1">Acesse o contrato de locação do seu imóvel</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Contrato de Locação</CardTitle>
          <CardDescription>Versão mais recente do seu contrato assinado</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <Skeleton className="h-16 w-full rounded-lg" />
          ) : isError ? (
            <p className="text-sm text-destructive">Erro ao carregar dados do contrato.</p>
          ) : contractGenerated ? (
            <>
              <div className="flex items-center gap-3 p-4 rounded-lg bg-muted/50 border">
                <FileText className="h-10 w-10 text-muted-foreground shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">contrato.pdf</p>
                  <p className="text-xs text-muted-foreground">Contrato de locação residencial</p>
                </div>
                <CheckCircle className="h-5 w-5 text-green-500 shrink-0" />
              </div>

              <Button
                className="w-full"
                onClick={() => void handleDownload()}
                disabled={downloadContract.isPending}
              >
                {downloadContract.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Preparando download...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Baixar Contrato (PDF)
                  </>
                )}
              </Button>
            </>
          ) : (
            <div className="flex flex-col items-center gap-2 p-6 rounded-lg bg-muted/50 border text-center">
              <Clock className="h-8 w-8 text-muted-foreground" />
              <p className="text-sm font-medium">Contrato ainda não foi gerado</p>
              <p className="text-xs text-muted-foreground">
                Assim que o contrato for gerado pelo gestor, ele ficará disponível aqui.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Dúvidas sobre o contrato?</AlertTitle>
        <AlertDescription>
          Entre em contato com o seu gestor de imóveis para esclarecimentos sobre as cláusulas
          contratuais.
        </AlertDescription>
      </Alert>
    </div>
  );
}
