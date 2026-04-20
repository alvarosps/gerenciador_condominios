'use client';

import { useState } from 'react';
import { Copy, Check, Loader2, AlertCircle, TrendingDown } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
  useTenantPayments,
  useTenantRentAdjustments,
  useGeneratePix,
} from '@/lib/api/hooks/use-tenant-payments';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';
import { getErrorMessage } from '@/lib/utils/error-handler';

function PixSection() {
  const [pixPayload, setPixPayload] = useState<string | null>(null);
  const [pixAmount, setPixAmount] = useState<string | null>(null);
  const [pixRecipient, setPixRecipient] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const generatePix = useGeneratePix();

  const handleGenerate = async () => {
    try {
      const result = await generatePix.mutateAsync(undefined);
      setPixPayload(result.pix_payload);
      setPixAmount(result.amount);
      setPixRecipient(result.recipient);
    } catch (error) {
      toast.error(getErrorMessage(error, 'Erro ao gerar código PIX'));
    }
  };

  const handleCopy = async () => {
    if (!pixPayload) return;
    await navigator.clipboard.writeText(pixPayload);
    setCopied(true);
    toast.success('Código PIX copiado!');
    setTimeout(() => {
      setCopied(false);
    }, 2000);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pagar com PIX</CardTitle>
        <CardDescription>Gere um código PIX para pagar seu aluguel</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {pixPayload ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>Destinatário: {pixRecipient}</span>
              <span className="font-medium text-foreground">{formatCurrency(pixAmount)}</span>
            </div>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded-md bg-muted p-3 text-xs break-all">{pixPayload}</code>
              <Button variant="outline" size="icon" onClick={() => void handleCopy()}>
                {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
              </Button>
            </div>
            <Button variant="outline" className="w-full" onClick={() => void handleGenerate()}>
              Gerar novo código
            </Button>
          </div>
        ) : (
          <Button
            className="w-full"
            onClick={() => void handleGenerate()}
            disabled={generatePix.isPending}
          >
            {generatePix.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Gerando código...
              </>
            ) : (
              'Gerar código PIX'
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function PaymentHistorySkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="flex items-center justify-between py-2">
          <div className="space-y-1">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-24" />
          </div>
          <Skeleton className="h-5 w-20" />
        </div>
      ))}
    </div>
  );
}

function PaymentHistorySection() {
  const { data: payments, isLoading, error } = useTenantPayments();

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Erro</AlertTitle>
        <AlertDescription>Não foi possível carregar o histórico de pagamentos.</AlertDescription>
      </Alert>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Histórico de Pagamentos</CardTitle>
        <CardDescription>Seus últimos pagamentos registrados</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <PaymentHistorySkeleton />
        ) : !payments || payments.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Nenhum pagamento registrado ainda.
          </p>
        ) : (
          <div className="divide-y">
            {payments.map((payment) => (
              <div key={payment.id} className="flex items-center justify-between py-3">
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">{payment.reference_month}</p>
                  <p className="text-xs text-muted-foreground">
                    Pago em {formatDate(payment.payment_date)}
                  </p>
                  {payment.notes ? (
                    <p className="text-xs text-muted-foreground">{payment.notes}</p>
                  ) : null}
                </div>
                <Badge variant="secondary" className="font-mono">
                  {formatCurrency(payment.amount_paid)}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RentAdjustmentSection() {
  const { data: adjustments, isLoading, error } = useTenantRentAdjustments();

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Erro</AlertTitle>
        <AlertDescription>Não foi possível carregar o histórico de reajustes.</AlertDescription>
      </Alert>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingDown className="h-5 w-5" />
          Reajustes de Aluguel
        </CardTitle>
        <CardDescription>Histórico de reajustes do seu contrato</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <PaymentHistorySkeleton />
        ) : !adjustments || adjustments.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Nenhum reajuste registrado.
          </p>
        ) : (
          <div className="divide-y">
            {adjustments.map((adjustment) => (
              <div key={adjustment.id} className="py-3 space-y-1">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">{formatDate(adjustment.adjustment_date)}</p>
                  <Badge variant="outline">+{adjustment.percentage}%</Badge>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>{formatCurrency(adjustment.previous_value)}</span>
                  <span>→</span>
                  <span className="text-foreground font-medium">
                    {formatCurrency(adjustment.new_value)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function TenantPaymentsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Pagamentos</h1>
        <p className="text-muted-foreground mt-1">Gerencie seus pagamentos de aluguel</p>
      </div>

      <PixSection />

      <Separator />

      <PaymentHistorySection />

      <RentAdjustmentSection />
    </div>
  );
}
