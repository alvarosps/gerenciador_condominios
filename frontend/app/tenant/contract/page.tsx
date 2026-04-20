'use client';

import { FileText, Download, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useDownloadContract } from '@/lib/api/hooks/use-tenant-notifications';
import { getErrorMessage } from '@/lib/utils/error-handler';

export default function TenantContractPage() {
  const downloadContract = useDownloadContract();

  const handleDownload = async () => {
    try {
      await downloadContract.mutateAsync();
      toast.success('Download do contrato iniciado!');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Erro ao baixar contrato'));
    }
  };

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
