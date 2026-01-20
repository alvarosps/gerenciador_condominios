'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent } from '@/components/ui/card';
import { FilePlus, Download, CheckCircle, Info, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useGenerateContract } from '@/lib/api/hooks/use-leases';
import { Lease } from '@/lib/schemas/lease.schema';
import { formatCurrency } from '@/lib/utils/formatters';
import { format, parseISO } from 'date-fns';

interface Props {
  open: boolean;
  lease: Lease | null;
  onClose: () => void;
}

export function ContractGenerateModal({ open, lease, onClose }: Props) {
  const generateMutation = useGenerateContract();
  const [pdfPath, setPdfPath] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!lease?.id) return;

    try {
      const result = await generateMutation.mutateAsync(lease.id);
      setPdfPath(result.pdf_path);
      toast.success(result.message || 'Contrato gerado com sucesso!');
    } catch (error) {
      toast.error('Erro ao gerar contrato');
      console.error('Contract generation error:', error);
    }
  };

  const handleDownload = () => {
    if (pdfPath) {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
      // Extract relative path from full Windows path (e.g., "C:\...\contracts\836\file.pdf" -> "contracts/836/file.pdf")
      const relativePath = pdfPath.replace(/\\/g, '/').replace(/^.*?(contracts\/)/, '$1');
      const downloadUrl = `${apiUrl.replace('/api', '')}/${relativePath}`;
      window.open(downloadUrl, '_blank');
    }
  };

  const handleClose = () => {
    setPdfPath(null);
    onClose();
  };

  if (!lease) return null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Gerar Contrato PDF</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {pdfPath ? (
            <div className="border border-green-200 bg-green-50 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="space-y-2 flex-1 min-w-0">
                  <p className="font-medium text-green-900">Contrato Gerado com Sucesso!</p>
                  <p className="text-sm text-green-800">
                    O contrato foi gerado e salvo no servidor.
                  </p>
                  <p className="text-sm text-green-800">
                    Clique em &quot;Baixar Contrato&quot; para visualizar o PDF.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <>
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription className="ml-2">
                  <p className="font-medium">Confirme os Dados da Locação</p>
                  <p className="text-sm text-muted-foreground">
                    Revise as informações abaixo antes de gerar o contrato PDF.
                  </p>
                </AlertDescription>
              </Alert>

              <Card>
                <CardContent className="pt-6">
                  <dl className="space-y-3">
                    <div className="flex justify-between py-2 border-b">
                      <dt className="font-medium text-sm text-gray-600">Apartamento</dt>
                      <dd className="text-sm text-gray-900">
                        {lease.apartment?.building?.name} - Apto {lease.apartment?.number}
                      </dd>
                    </div>
                    <div className="flex justify-between py-2 border-b">
                      <dt className="font-medium text-sm text-gray-600">Inquilino Responsável</dt>
                      <dd className="text-sm text-gray-900">
                        {lease.responsible_tenant?.name}
                      </dd>
                    </div>
                    <div className="flex justify-between py-2 border-b">
                      <dt className="font-medium text-sm text-gray-600">Total de Inquilinos</dt>
                      <dd className="text-sm text-gray-900">
                        {lease.tenants?.length || 0}
                      </dd>
                    </div>
                    <div className="flex justify-between py-2 border-b">
                      <dt className="font-medium text-sm text-gray-600">Data de Início</dt>
                      <dd className="text-sm text-gray-900">
                        {format(parseISO(lease.start_date), 'dd/MM/yyyy')}
                      </dd>
                    </div>
                    <div className="flex justify-between py-2 border-b">
                      <dt className="font-medium text-sm text-gray-600">Validade</dt>
                      <dd className="text-sm text-gray-900">
                        {lease.validity_months} meses
                      </dd>
                    </div>
                    <div className="flex justify-between py-2 border-b">
                      <dt className="font-medium text-sm text-gray-600">Valor do Aluguel</dt>
                      <dd className="text-sm text-gray-900">
                        {formatCurrency(lease.rental_value)}
                      </dd>
                    </div>
                    <div className="flex justify-between py-2 border-b">
                      <dt className="font-medium text-sm text-gray-600">Taxa de Limpeza</dt>
                      <dd className="text-sm text-gray-900">
                        {formatCurrency(lease.cleaning_fee)}
                      </dd>
                    </div>
                    <div className="flex justify-between py-2 border-b">
                      <dt className="font-medium text-sm text-gray-600">Taxa de Tag</dt>
                      <dd className="text-sm text-gray-900">
                        {formatCurrency(lease.tag_fee)}
                      </dd>
                    </div>
                    <div className="flex justify-between py-2">
                      <dt className="font-medium text-sm text-gray-600">Dia de Vencimento</dt>
                      <dd className="text-sm text-gray-900">
                        Dia {lease.due_day} de cada mês
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>

              {generateMutation.isPending && (
                <div className="flex flex-col items-center justify-center py-6 space-y-3">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <p className="text-sm text-muted-foreground">
                    Gerando contrato PDF... Isso pode levar alguns segundos.
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Fechar
          </Button>
          {pdfPath ? (
            <Button onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Baixar Contrato
            </Button>
          ) : (
            <Button
              onClick={handleGenerate}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <FilePlus className="h-4 w-4 mr-2" />
              )}
              Gerar Contrato
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
