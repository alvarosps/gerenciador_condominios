'use client';

import { Bell, BellOff, CheckCheck, Loader2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  useTenantNotifications,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
} from '@/lib/api/hooks/use-tenant-notifications';
import { getErrorMessage } from '@/lib/utils/error-handler';
import { formatDate } from '@/lib/utils/formatters';

function NotificationsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-start gap-3 p-3 rounded-lg border">
          <Skeleton className="h-2 w-2 rounded-full mt-2 shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function TenantNotificationsPage() {
  const { data: notifications, isLoading, error } = useTenantNotifications();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const unreadCount = notifications?.filter((n) => !n.is_read).length ?? 0;

  const handleMarkRead = async (id: number) => {
    try {
      await markRead.mutateAsync(id);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Erro ao marcar notificação como lida'));
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllRead.mutateAsync();
      toast.success('Todas as notificações marcadas como lidas');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Erro ao marcar todas como lidas'));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bell className="h-6 w-6" />
            Notificações
          </h1>
          <p className="text-muted-foreground mt-1">
            {unreadCount > 0 ? `${unreadCount} não lida${unreadCount > 1 ? 's' : ''}` : 'Tudo em dia'}
          </p>
        </div>
        {unreadCount > 0 ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => void handleMarkAllRead()}
            disabled={markAllRead.isPending}
          >
            {markAllRead.isPending ? (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <CheckCheck className="h-4 w-4 mr-1" />
            )}
            Marcar todas como lidas
          </Button>
        ) : null}
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erro</AlertTitle>
          <AlertDescription>Não foi possível carregar as notificações.</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Avisos</CardTitle>
          <CardDescription>Mensagens do seu gestor de imóveis</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <NotificationsSkeleton />
          ) : !notifications || notifications.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-8 text-muted-foreground">
              <BellOff className="h-10 w-10" />
              <p className="text-sm">Sem notificações no momento.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {notifications.map((notification) => (
                <button
                  key={notification.id}
                  type="button"
                  className={`w-full text-left flex items-start gap-3 p-3 rounded-lg border transition-colors hover:bg-muted/50 ${
                    !notification.is_read ? 'bg-primary/5 border-primary/20' : 'border-border'
                  }`}
                  onClick={() => {
                    if (!notification.is_read) void handleMarkRead(notification.id);
                  }}
                >
                  <span
                    className={`mt-2 h-2 w-2 rounded-full shrink-0 ${
                      notification.is_read ? 'bg-transparent' : 'bg-primary'
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium truncate">{notification.title}</p>
                      {!notification.is_read ? (
                        <Badge variant="secondary" className="shrink-0 text-xs">
                          Nova
                        </Badge>
                      ) : null}
                    </div>
                    <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">
                      {notification.body}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDate(notification.sent_at)}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
