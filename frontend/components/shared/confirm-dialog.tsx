import { createRoot } from 'react-dom/client';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { AlertTriangle } from 'lucide-react';

interface ConfirmDialogOptions {
  title: string;
  content: string;
  onOk: () => void | Promise<void>;
  onCancel?: () => void;
  okText?: string;
  cancelText?: string;
  okType?: 'default' | 'destructive';
}

export function showConfirmDialog({
  title,
  content,
  onOk,
  onCancel,
  okText = 'Confirmar',
  cancelText = 'Cancelar',
  okType = 'default',
}: ConfirmDialogOptions): void {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);

  const cleanup = (): void => {
    setTimeout(() => {
      root.unmount();
      document.body.removeChild(container);
    }, 300); // Wait for animation to complete
  };

  const handleOk = async (): Promise<void> => {
    try {
      await onOk();
    } finally {
      cleanup();
    }
  };

  const handleCancel = (): void => {
    onCancel?.();
    cleanup();
  };

  root.render(
    <AlertDialog defaultOpen>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            {title}
          </AlertDialogTitle>
          <AlertDialogDescription>{content}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel}>
            {cancelText}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleOk}
            className={
              okType === 'destructive'
                ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90'
                : ''
            }
          >
            {okText}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export function showDeleteConfirm(
  itemName: string,
  onConfirm: () => void | Promise<void>
): void {
  showConfirmDialog({
    title: 'Confirmar exclusão',
    content: `Tem certeza que deseja excluir ${itemName}? Esta ação não pode ser desfeita.`,
    onOk: onConfirm,
    okText: 'Excluir',
    okType: 'destructive',
  });
}
