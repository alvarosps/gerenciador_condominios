'use client';

import React, { useState, useCallback } from 'react';
import { GripVertical, Plus, Pencil, Trash2, Eye, EyeOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import {
  useContractRules,
  useCreateContractRule,
  useUpdateContractRule,
  useDeleteContractRule,
  useReorderContractRules,
  useToggleContractRule,
  ContractRule,
} from '@/lib/api/hooks/use-contract-rules';
import { RuleEditModal } from './rule-edit-modal';
import { showDeleteConfirm } from '@/components/shared/confirm-dialog';

/**
 * RulesEditor Component
 *
 * Manages contract rules with:
 * - Drag-and-drop reordering
 * - Inline toggle for active/inactive
 * - Edit modal with rich text editor
 * - Delete with confirmation
 * - Add new rule
 */
export function RulesEditor() {
  const { data: rules, isLoading, error } = useContractRules();
  const createMutation = useCreateContractRule();
  const updateMutation = useUpdateContractRule();
  const deleteMutation = useDeleteContractRule();
  const reorderMutation = useReorderContractRules();
  const toggleMutation = useToggleContractRule();

  // Modal states
  const [editingRule, setEditingRule] = useState<ContractRule | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Drag state
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);

  // Handle drag start
  const handleDragStart = useCallback((e: React.DragEvent, id: number) => {
    setDraggedId(id);
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  // Handle drag over
  const handleDragOver = useCallback((e: React.DragEvent, id: number) => {
    e.preventDefault();
    if (draggedId !== id) {
      setDragOverId(id);
    }
  }, [draggedId]);

  // Handle drag end
  const handleDragEnd = useCallback(() => {
    if (draggedId && dragOverId && draggedId !== dragOverId && rules) {
      const draggedIndex = rules.findIndex((r) => r.id === draggedId);
      const dragOverIndex = rules.findIndex((r) => r.id === dragOverId);

      if (draggedIndex !== -1 && dragOverIndex !== -1) {
        // Create new order array
        const newRules = [...rules];
        const [draggedItem] = newRules.splice(draggedIndex, 1);
        newRules.splice(dragOverIndex, 0, draggedItem);

        // Send reorder request
        const newOrder = newRules.map((r) => r.id);
        reorderMutation.mutate(newOrder, {
          onSuccess: () => {
            toast.success('Ordem das regras atualizada');
          },
          onError: () => {
            toast.error('Erro ao reordenar regras');
          },
        });
      }
    }

    setDraggedId(null);
    setDragOverId(null);
  }, [draggedId, dragOverId, rules, reorderMutation]);

  // Handle toggle active
  const handleToggleActive = useCallback(
    (id: number, currentState: boolean) => {
      toggleMutation.mutate(
        { id, is_active: !currentState },
        {
          onSuccess: () => {
            toast.success(!currentState ? 'Regra ativada' : 'Regra desativada');
          },
          onError: () => {
            toast.error('Erro ao alterar status da regra');
          },
        }
      );
    },
    [toggleMutation]
  );

  // Handle create
  const handleCreate = useCallback(
    (content: string) => {
      createMutation.mutate(
        { content, is_active: true },
        {
          onSuccess: () => {
            toast.success('Regra criada com sucesso');
            setIsCreateModalOpen(false);
          },
          onError: () => {
            toast.error('Erro ao criar regra');
          },
        }
      );
    },
    [createMutation]
  );

  // Handle update
  const handleUpdate = useCallback(
    (id: number, content: string) => {
      updateMutation.mutate(
        { id, content },
        {
          onSuccess: () => {
            toast.success('Regra atualizada com sucesso');
            setEditingRule(null);
          },
          onError: () => {
            toast.error('Erro ao atualizar regra');
          },
        }
      );
    },
    [updateMutation]
  );

  // Handle delete with confirmation
  const handleDeleteClick = useCallback(
    (id: number) => {
      showDeleteConfirm('esta regra', () => {
        deleteMutation.mutate(id, {
          onSuccess: () => {
            toast.success('Regra excluída com sucesso');
          },
          onError: () => {
            toast.error('Erro ao excluir regra');
          },
        });
      });
    },
    [deleteMutation]
  );

  // Strip HTML for preview
  const stripHtml = (html: string): string => {
    return html.replace(/<[^>]+>/g, '');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-destructive">
        Erro ao carregar regras. Tente novamente.
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle>Regras do Condomínio</CardTitle>
          <CardDescription>
            Gerencie as regras que aparecem nos contratos de locação
          </CardDescription>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)} size="sm">
          <Plus className="w-4 h-4 mr-2" />
          Nova Regra
        </Button>
      </CardHeader>
      <CardContent>
        {rules && rules.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            Nenhuma regra cadastrada. Clique em "Nova Regra" para adicionar.
          </div>
        ) : (
          <div className="space-y-2">
            {rules?.map((rule, index) => (
              <div
                key={rule.id}
                draggable
                onDragStart={(e) => handleDragStart(e, rule.id)}
                onDragOver={(e) => handleDragOver(e, rule.id)}
                onDragEnd={handleDragEnd}
                className={cn(
                  'flex items-start gap-3 p-3 rounded-lg border bg-card transition-all',
                  draggedId === rule.id && 'opacity-50',
                  dragOverId === rule.id && 'border-primary border-2',
                  !rule.is_active && 'opacity-60 bg-muted/50'
                )}
              >
                {/* Drag Handle */}
                <div className="cursor-grab active:cursor-grabbing pt-1">
                  <GripVertical className="w-5 h-5 text-muted-foreground" />
                </div>

                {/* Order Number */}
                <div className="flex items-center justify-center w-6 h-6 rounded-full bg-muted text-muted-foreground text-sm font-medium">
                  {index + 1}
                </div>

                {/* Content Preview */}
                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      'text-sm line-clamp-2',
                      !rule.is_active && 'text-muted-foreground'
                    )}
                    title={stripHtml(rule.content)}
                  >
                    {stripHtml(rule.content)}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Active Toggle */}
                  <div className="flex items-center gap-1.5">
                    {rule.is_active ? (
                      <Eye className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <EyeOff className="w-4 h-4 text-muted-foreground" />
                    )}
                    <Switch
                      checked={rule.is_active}
                      onCheckedChange={() => handleToggleActive(rule.id, rule.is_active)}
                      disabled={toggleMutation.isPending}
                    />
                  </div>

                  {/* Edit Button */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setEditingRule(rule)}
                    className="h-8 w-8"
                  >
                    <Pencil className="w-4 h-4" />
                  </Button>

                  {/* Delete Button */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteClick(rule.id)}
                    className="h-8 w-8 text-destructive hover:text-destructive"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Reorder Loading Indicator */}
        {reorderMutation.isPending && (
          <div className="flex items-center justify-center py-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            Salvando ordem...
          </div>
        )}
      </CardContent>

      {/* Create Modal */}
      <RuleEditModal
        open={isCreateModalOpen}
        onOpenChange={setIsCreateModalOpen}
        onSave={handleCreate}
        isLoading={createMutation.isPending}
        title="Nova Regra"
      />

      {/* Edit Modal */}
      <RuleEditModal
        open={!!editingRule}
        onOpenChange={(open) => !open && setEditingRule(null)}
        onSave={(content) => editingRule && handleUpdate(editingRule.id, content)}
        initialContent={editingRule?.content}
        isLoading={updateMutation.isPending}
        title="Editar Regra"
      />
    </Card>
  );
}
