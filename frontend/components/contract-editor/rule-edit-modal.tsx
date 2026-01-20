'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Loader2 } from 'lucide-react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface RuleEditModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (content: string) => void;
  initialContent?: string;
  isLoading?: boolean;
  title?: string;
}

/**
 * Modal for editing contract rules with a simple rich text editor.
 * Supports bold, italic, and underline formatting.
 */
export function RuleEditModal({
  open,
  onOpenChange,
  onSave,
  initialContent = '',
  isLoading = false,
  title = 'Editar Regra',
}: RuleEditModalProps) {
  const [content, setContent] = useState(initialContent);

  // Simple editor extensions (just basic formatting)
  // Extensions are created fresh each time to avoid duplicate warnings on remount
  const extensions = [
    StarterKit.configure({
      heading: false,
      bulletList: false,
      orderedList: false,
      blockquote: false,
      codeBlock: false,
      horizontalRule: false,
    }),
    Underline,
  ];

  const editor = useEditor({
    extensions,
    content: initialContent,
    immediatelyRender: false,
    shouldRerenderOnTransaction: false,
    editorProps: {
      attributes: {
        class: cn(
          'prose prose-sm max-w-none focus:outline-none min-h-[150px] p-3',
          'border rounded-md'
        ),
      },
    },
    onUpdate: ({ editor: currentEditor }) => {
      setContent(currentEditor.getHTML());
    },
  }, [open]); // Recreate editor when modal opens/closes to ensure clean state

  // Reset editor content when modal opens with new content
  useEffect(() => {
    if (open && editor) {
      editor.commands.setContent(initialContent || '<p></p>');
      setContent(initialContent || '');
    }
  }, [open, initialContent, editor]);

  // Handle save
  const handleSave = useCallback(() => {
    if (content.trim() && content !== '<p></p>') {
      onSave(content);
    }
  }, [content, onSave]);

  // Check if content is empty
  const isEmpty = !content.trim() || content === '<p></p>';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Digite o texto da regra. Use a barra de ferramentas para formatar (negrito, itálico, sublinhado).
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {/* Formatting Toolbar */}
          {editor && (
            <div className="flex items-center gap-1 mb-2 p-1 border rounded-md bg-muted/50">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => editor.chain().focus().toggleBold().run()}
                className={cn(
                  'h-8 px-2',
                  editor.isActive('bold') && 'bg-accent'
                )}
              >
                <span className="font-bold">B</span>
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => editor.chain().focus().toggleItalic().run()}
                className={cn(
                  'h-8 px-2',
                  editor.isActive('italic') && 'bg-accent'
                )}
              >
                <span className="italic">I</span>
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => editor.chain().focus().toggleUnderline().run()}
                className={cn(
                  'h-8 px-2',
                  editor.isActive('underline') && 'bg-accent'
                )}
              >
                <span className="underline">U</span>
              </Button>
            </div>
          )}

          {/* Editor Content */}
          <EditorContent editor={editor} className="rule-editor" />
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleSave}
            disabled={isLoading || isEmpty}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Salvando...
              </>
            ) : (
              'Salvar'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
