'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import {
  useContractTemplate,
  usePreviewContractTemplate,
} from '@/lib/api/hooks/use-contract-template';
import { useContractPdf } from '@/lib/api/hooks/use-leases';
import { type Lease } from '@/lib/schemas/lease.schema';

interface ContractViewModalProps {
  open: boolean;
  lease: Lease | null;
  onClose: () => void;
}

export function ContractViewModal({ open, lease, onClose }: ContractViewModalProps) {
  const [previewHtml, setPreviewHtml] = useState('');
  const [pdfObjectUrl, setPdfObjectUrl] = useState<string | null>(null);
  const { data: template } = useContractTemplate();
  const previewMutation = usePreviewContractTemplate();
  const lastLeaseIdRef = useRef<number | null>(null);

  const wantsPdf = Boolean(open && lease?.contract_generated);
  // Fetch the PDF via the same-origin API proxy (carries HttpOnly auth cookies) instead of
  // building an anonymous /contracts/ URL; the iframe shows the resulting object URL.
  const { data: pdfBlob } = useContractPdf(lease?.id ?? null, wantsPdf);
  const showPdf = wantsPdf && Boolean(pdfObjectUrl);

  useEffect(() => {
    if (!pdfBlob) {
      return;
    }
    const objectUrl = URL.createObjectURL(pdfBlob);
    setPdfObjectUrl(objectUrl);
    return () => {
      URL.revokeObjectURL(objectUrl);
      setPdfObjectUrl(null);
    };
  }, [pdfBlob]);

  const loadPreview = useCallback(
    async (templateContent: string, leaseId: number) => {
      try {
        const result = await previewMutation.mutateAsync({
          content: templateContent,
          lease_id: leaseId,
        });
        setPreviewHtml(result.html);
      } catch {
        toast.error('Erro ao gerar preview do contrato');
      }
    },
    [previewMutation]
  );

  useEffect(() => {
    if (!open || !lease?.id || wantsPdf) {
      setPreviewHtml('');
      lastLeaseIdRef.current = null;
      return;
    }

    if (template?.content && lastLeaseIdRef.current !== lease.id) {
      lastLeaseIdRef.current = lease.id;
      void loadPreview(template.content, lease.id);
    }
  }, [open, lease?.id, wantsPdf, template?.content, loadPreview]);

  const tenantName = lease?.responsible_tenant?.name ?? 'Inquilino';
  const aptInfo = lease?.apartment ? `Apto ${String(lease.apartment.number)}` : '';

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>
            Contrato — {tenantName} {aptInfo ? `(${aptInfo})` : ''}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 min-h-[60vh] rounded-md border overflow-hidden">
          {showPdf && pdfObjectUrl ? (
            <iframe
              src={pdfObjectUrl}
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
