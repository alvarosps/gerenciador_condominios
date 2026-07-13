'use client';

import { useState, useRef } from 'react';
import { Upload, FileText, Loader2, AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  useUploadProof,
  useTenantProofs,
  type PaymentProof,
} from '@/lib/api/hooks/use-tenant-payments';
import { formatDate } from '@/lib/utils/formatters';
import { getErrorMessage } from '@/lib/utils/error-handler';

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'application/pdf'];
const ALLOWED_EXTENSIONS = '.jpg, .jpeg, .png, .pdf';

function proofStatusBadge(status: PaymentProof['status']) {
  switch (status) {
    case 'approved':
      return (
        <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
          <CheckCircle className="h-3 w-3 mr-1" />
          Aprovado
        </Badge>
      );
    case 'rejected':
      return (
        <Badge variant="destructive">
          <XCircle className="h-3 w-3 mr-1" />
          Rejeitado
        </Badge>
      );
    default:
      return (
        <Badge variant="secondary">
          <Clock className="h-3 w-3 mr-1" />
          Pendente
        </Badge>
      );
  }
}

function UploadForm() {
  const [referenceMonth, setReferenceMonth] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadProof = useUploadProof();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setFileError(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
      setFileError('Tipo de arquivo não permitido. Use JPEG, PNG ou PDF.');
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setFileError('Arquivo muito grande. O tamanho máximo é 10 MB.');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedFile) {
      toast.error('Selecione um arquivo para enviar.');
      return;
    }

    if (!referenceMonth) {
      toast.error('Informe o mês de referência.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    // The <input type="month"> value is "YYYY-MM"; the backend DateField expects a full date.
    formData.append('reference_month', `${referenceMonth}-01`);

    try {
      await uploadProof.mutateAsync(formData);
      toast.success('Comprovante enviado com sucesso!');
      setSelectedFile(null);
      setReferenceMonth('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      toast.error(getErrorMessage(error, 'Erro ao enviar comprovante'));
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Enviar Comprovante
        </CardTitle>
        <CardDescription>
          Envie o comprovante de pagamento do seu aluguel (JPEG, PNG ou PDF, máx. 10 MB)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="reference_month">Mês de Referência</Label>
            <Input
              id="reference_month"
              type="month"
              value={referenceMonth}
              onChange={(e) => setReferenceMonth(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="proof_file">Arquivo</Label>
            <Input
              id="proof_file"
              type="file"
              accept={ALLOWED_EXTENSIONS}
              onChange={handleFileChange}
              ref={fileInputRef}
              required
            />
            {fileError ? (
              <p className="text-sm text-destructive">{fileError}</p>
            ) : selectedFile ? (
              <p className="text-sm text-muted-foreground flex items-center gap-1">
                <FileText className="h-3 w-3" />
                {selectedFile.name} ({(selectedFile.size / 1024).toFixed(0)} KB)
              </p>
            ) : null}
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={uploadProof.isPending || !selectedFile || !referenceMonth}
          >
            {uploadProof.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Enviando...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Enviar Comprovante
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function ProofStatusCard({ proof }: { proof: PaymentProof }) {
  return (
    <div className="flex items-start justify-between py-3 border-b last:border-0">
      <div className="space-y-1">
        <p className="text-sm font-medium">{proof.reference_month}</p>
        <p className="text-xs text-muted-foreground">Enviado em {formatDate(proof.created_at)}</p>
        {proof.reviewed_at ? (
          <p className="text-xs text-muted-foreground">
            Revisado em {formatDate(proof.reviewed_at)}
          </p>
        ) : null}
        {proof.status === 'rejected' && proof.rejection_reason ? (
          <p className="text-xs text-destructive">{proof.rejection_reason}</p>
        ) : null}
      </div>
      {proofStatusBadge(proof.status)}
    </div>
  );
}

export default function TenantProofPage() {
  const { data: proofs, isLoading, isError } = useTenantProofs();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Comprovante de Pagamento</h1>
        <p className="text-muted-foreground mt-1">
          Envie o comprovante do seu pagamento de aluguel
        </p>
      </div>

      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Importante</AlertTitle>
        <AlertDescription>
          O comprovante será analisado e você receberá uma notificação quando for aprovado ou
          rejeitado.
        </AlertDescription>
      </Alert>

      <UploadForm />

      <Card>
        <CardHeader>
          <CardTitle>Comprovantes Enviados</CardTitle>
          <CardDescription>Status dos comprovantes enviados</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : isError ? (
            <p className="text-sm text-destructive">Erro ao carregar comprovantes.</p>
          ) : proofs && proofs.length > 0 ? (
            proofs.map((proof) => <ProofStatusCard key={proof.id} proof={proof} />)
          ) : (
            <p className="text-sm text-muted-foreground">Nenhum comprovante enviado ainda.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
