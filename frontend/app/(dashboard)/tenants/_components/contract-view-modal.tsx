'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useContractTemplate, usePreviewContractTemplate } from '@/lib/api/hooks/use-contract-template';
import { type Lease } from '@/lib/schemas/lease.schema';

interface ContractViewModalProps {
  open: boolean;
  lease: Lease | null;
  onClose: () => void;
}

function getContractPdfUrl(lease: Lease): string | null {
  if (!lease.contract_generated) return null;
  const buildingNumber = lease.apartment?.building?.street_number;
  const aptNumber = lease.apartment?.number;
  const leaseId = lease.id;
  if (!buildingNumber || !aptNumber || !leaseId) return null;

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api';
  const baseUrl = apiUrl.replace(/\/api\/?$/, '');
  return `${baseUrl}/contracts/${String(buildingNumber)}/contract_apto_${String(aptNumber)}_${String(leaseId)}.pdf`;
}

export function ContractViewModal({ open, lease, onClose }: ContractViewModalProps) {
  const [previewHtml, setPreviewHtml] = useState('');
  const { data: template } = useContractTemplate();
  const previewMutation = usePreviewContractTemplate();
  const lastLeaseIdRef = useRef<number | null>(null);

  const pdfUrl = lease ? getContractPdfUrl(lease) : null;
  const showPdf = lease?.contract_generated && pdfUrl;

  const loadPreview = useCallback(async (templateContent: string, leaseId: number) => {
    try {
      const result = await previewMutation.mutateAsync({ content: templateContent, lease_id: leaseId });
      setPreviewHtml(result.html);
    } catch {
      toast.error('Erro ao gerar preview do contrato');
    }
  }, [previewMutation]);

  useEffect(() => {
    if (!open || !lease?.id || showPdf) {
      setPreviewHtml('');
      lastLeaseIdRef.current = null;
      return;
    }

    if (template?.content && lastLeaseIdRef.current !== lease.id) {
      lastLeaseIdRef.current = lease.id;
      void loadPreview(template.content, lease.id);
    }
  }, [open, lease?.id, showPdf, template?.content, loadPreview]);

  const tenantName = lease?.responsible_tenant?.name ?? 'Inquilino';
  const aptInfo = lease?.apartment
    ? `Apto ${String(lease.apartment.number)}`
    : '';

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>
            Contrato — {tenantName} {aptInfo ? `(${aptInfo})` : ''}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 min-h-[60vh] rounded-md border overflow-hidden">
          {showPdf ? (
            <iframe
              src={pdfUrl}
              className="w-full h-full min-h-[60vh]"
              title="Contrato PDF"
            />
          ) : previewHtml ? (
            <iframe
              srcDoc={previewHtml}
              className="w-full h-full min-h-[60vh] bg-white"
              title="Preview do Contrato"
            />
          ) : (
            <div className="flex items-center justify-center h-full min-h-[60vh]">
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Gerando preview...</p>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
