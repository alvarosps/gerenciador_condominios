'use client';

import { useState } from 'react';
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
import { Loader2, Trash2 } from 'lucide-react';

interface DeleteConfirmDialogProps {
  /**
   * Whether the dialog is open
   */
  open: boolean;
  /**
   * Called when the dialog should close (cancel or after successful delete)
   */
  onOpenChange: (open: boolean) => void;
  /**
   * Title of the dialog
   */
  title?: string;
  /**
   * Description/warning message
   */
  description?: string;
  /**
   * The name of the item being deleted (for default description)
   */
  itemName?: string;
  /**
   * Callback when delete is confirmed. Should return a promise if async.
   */
  onConfirm: () => void | Promise<void>;
  /**
   * Whether the delete action is currently loading
   */
  isLoading?: boolean;
}

/**
 * A reusable delete confirmation dialog component.
 *
 * Usage:
 * ```tsx
 * const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
 * const [itemToDelete, setItemToDelete] = useState<Item | null>(null);
 *
 * <DeleteConfirmDialog
 *   open={deleteDialogOpen}
 *   onOpenChange={setDeleteDialogOpen}
 *   itemName={itemToDelete?.name}
 *   onConfirm={handleDelete}
 *   isLoading={isDeleting}
 * />
 * ```
 */
export function DeleteConfirmDialog({
  open,
  onOpenChange,
  title = 'Confirmar exclusão',
  description,
  itemName,
  onConfirm,
  isLoading = false,
}: DeleteConfirmDialogProps) {
  const [internalLoading, setInternalLoading] = useState(false);

  const actualLoading = isLoading || internalLoading;

  const defaultDescription = itemName
    ? `Tem certeza que deseja excluir "${itemName}"? Esta ação não pode ser desfeita.`
    : 'Tem certeza que deseja excluir este item? Esta ação não pode ser desfeita.';

  const handleConfirm = async () => {
    try {
      setInternalLoading(true);
      await onConfirm();
      onOpenChange(false);
    } finally {
      setInternalLoading(false);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            {title}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {description || defaultDescription}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={actualLoading}>
            Cancelar
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              handleConfirm();
            }}
            disabled={actualLoading}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {actualLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Excluindo...
              </>
            ) : (
              'Excluir'
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

/**
 * Props for bulk delete confirmation dialog
 */
interface BulkDeleteConfirmDialogProps {
  /**
   * Whether the dialog is open
   */
  open: boolean;
  /**
   * Called when the dialog should close
   */
  onOpenChange: (open: boolean) => void;
  /**
   * Number of items to be deleted
   */
  count: number;
  /**
   * Entity name (plural form, e.g., "inquilinos", "apartamentos")
   */
  entityName?: string;
  /**
   * Callback when delete is confirmed
   */
  onConfirm: () => void | Promise<void>;
  /**
   * Whether the delete action is currently loading
   */
  isLoading?: boolean;
}

/**
 * A reusable bulk delete confirmation dialog component.
 *
 * Usage:
 * ```tsx
 * <BulkDeleteConfirmDialog
 *   open={bulkDeleteOpen}
 *   onOpenChange={setBulkDeleteOpen}
 *   count={selectedIds.length}
 *   entityName="inquilinos"
 *   onConfirm={handleBulkDelete}
 *   isLoading={isBulkDeleting}
 * />
 * ```
 */
export function BulkDeleteConfirmDialog({
  open,
  onOpenChange,
  count,
  entityName = 'itens',
  onConfirm,
  isLoading = false,
}: BulkDeleteConfirmDialogProps) {
  const [internalLoading, setInternalLoading] = useState(false);

  const actualLoading = isLoading || internalLoading;

  const handleConfirm = async () => {
    try {
      setInternalLoading(true);
      await onConfirm();
      onOpenChange(false);
    } finally {
      setInternalLoading(false);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            Excluir {count} {entityName}
          </AlertDialogTitle>
          <AlertDialogDescription>
            Tem certeza que deseja excluir {count} {entityName} selecionados?
            Esta ação não pode ser desfeita.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={actualLoading}>
            Cancelar
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              handleConfirm();
            }}
            disabled={actualLoading}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {actualLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Excluindo...
              </>
            ) : (
              `Excluir ${count} ${entityName}`
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
