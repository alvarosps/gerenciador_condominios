'use client';

import { AlertCircle, Bell, BellOff } from 'lucide-react';
import { toast } from 'sonner';
import { Switch } from '@/components/ui/switch';
import { useWebPush } from '@/lib/api/hooks/use-web-push';
import { getErrorMessage } from '@/lib/utils/error-handler';

export function PushToggle() {
  const { isSupported, permission, isSubscribed, isPending, subscribe, unsubscribe } = useWebPush();

  const isDenied = permission === 'denied';
  const disabled = !isSupported || isDenied || isPending;

  const handleCheckedChange = async (checked: boolean) => {
    try {
      if (checked) {
        await subscribe();
        toast.success('Notificações ativadas');
      } else {
        await unsubscribe();
        toast.success('Notificações desativadas');
      }
    } catch (err) {
      toast.error(getErrorMessage(err, 'Erro ao atualizar notificações'));
    }
  };

  const status = !isSupported
    ? {
        icon: <BellOff className="h-4 w-4 text-muted-foreground" />,
        text: 'Notificações não são suportadas neste navegador.',
      }
    : isDenied
      ? {
          icon: <AlertCircle className="h-4 w-4 text-muted-foreground" />,
          text: 'Permissão de notificações bloqueada — habilite nas configurações do navegador.',
        }
      : isSubscribed
        ? {
            icon: <Bell className="h-4 w-4 text-muted-foreground" />,
            text: 'Notificações ativadas.',
          }
        : {
            icon: <BellOff className="h-4 w-4 text-muted-foreground" />,
            text: 'Ative para receber avisos no dispositivo.',
          };

  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-2">
        {status.icon}
        <div>
          <p className="text-sm font-medium">Ativar notificações</p>
          <p className="text-sm text-muted-foreground">{status.text}</p>
        </div>
      </div>
      <Switch
        checked={isSubscribed}
        disabled={disabled}
        aria-label="Ativar notificações"
        onCheckedChange={(checked) => void handleCheckedChange(checked)}
      />
    </div>
  );
}
