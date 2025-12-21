import { useState } from 'react';
import { message } from 'antd';
import type { Key } from 'antd/es/table/interface';

interface BulkOperationsOptions {
  entityName: string; // e.g., "prédio", "apartamento"
  entityNamePlural: string; // e.g., "prédios", "apartamentos"
}

/**
 * Custom hook for managing bulk operations in tables
 * Handles row selection and provides utilities for bulk actions
 */
export function useBulkOperations(options: BulkOperationsOptions) {
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);

  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
    selections: [
      {
        key: 'all',
        text: 'Selecionar Todos',
        onSelect: (changeableRowKeys: Key[]) => {
          setSelectedRowKeys(changeableRowKeys);
        },
      },
      {
        key: 'none',
        text: 'Desmarcar Todos',
        onSelect: () => {
          setSelectedRowKeys([]);
        },
      },
    ],
  };

  const clearSelection = () => {
    setSelectedRowKeys([]);
  };

  const handleBulkDelete = async (
    deleteFn: (id: number) => Promise<void>,
    onSuccess?: () => void
  ) => {
    if (selectedRowKeys.length === 0) {
      message.warning('Nenhum item selecionado');
      return;
    }

    const totalItems = selectedRowKeys.length;
    const itemText =
      totalItems === 1 ? options.entityName : options.entityNamePlural;

    try {
      // Delete all selected items in parallel
      await Promise.all(
        selectedRowKeys.map((key) => deleteFn(Number(key)))
      );

      message.success(
        `${totalItems} ${itemText} excluído${totalItems > 1 ? 's' : ''} com sucesso`
      );
      clearSelection();

      if (onSuccess) {
        onSuccess();
      }
    } catch (error) {
      console.error('Bulk delete error:', error);
      message.error(
        `Erro ao excluir ${itemText}. Alguns itens podem ter dependências.`
      );
    }
  };

  const handleBulkStatusChange = async <T extends { id?: number }>(
    items: T[],
    updateFn: (data: Partial<T> & { id: number }) => Promise<void>,
    statusField: keyof T,
    newStatus: unknown,
    onSuccess?: () => void
  ) => {
    if (selectedRowKeys.length === 0) {
      message.warning('Nenhum item selecionado');
      return;
    }

    const totalItems = selectedRowKeys.length;
    const itemText =
      totalItems === 1 ? options.entityName : options.entityNamePlural;

    try {
      // Get selected items
      const selectedItems = items.filter((item) =>
        selectedRowKeys.includes(item.id as Key)
      );

      // Update all selected items in parallel
      await Promise.all(
        selectedItems.map((item) =>
          updateFn({ id: item.id!, [statusField]: newStatus } as Partial<T> & { id: number })
        )
      );

      message.success(
        `Status de ${totalItems} ${itemText} atualizado${totalItems > 1 ? 's' : ''} com sucesso`
      );
      clearSelection();

      if (onSuccess) {
        onSuccess();
      }
    } catch (error) {
      console.error('Bulk status change error:', error);
      message.error(`Erro ao atualizar status de ${itemText}`);
    }
  };

  return {
    selectedRowKeys,
    rowSelection,
    clearSelection,
    handleBulkDelete,
    handleBulkStatusChange,
    hasSelection: selectedRowKeys.length > 0,
    selectionCount: selectedRowKeys.length,
  };
}
