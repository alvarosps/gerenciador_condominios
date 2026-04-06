import { useCallback, useState } from 'react';

export function useUnsavedChanges(isDirty: boolean) {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  const handleOpenChange = useCallback(
    (open: boolean, onClose: () => void) => {
      if (!open && isDirty) {
        setShowConfirmDialog(true);
      } else if (!open) {
        onClose();
      }
    },
    [isDirty],
  );

  const confirmDiscard = useCallback((onClose: () => void) => {
    setShowConfirmDialog(false);
    onClose();
  }, []);

  const cancelDiscard = useCallback(() => {
    setShowConfirmDialog(false);
  }, []);

  return { showConfirmDialog, handleOpenChange, confirmDiscard, cancelDiscard };
}
