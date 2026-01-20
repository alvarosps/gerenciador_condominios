'use client';

import React, { useCallback } from 'react';
import { Editor } from '@tiptap/react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Bold,
  Italic,
  Underline,
  Strikethrough,
  AlignLeft,
  AlignCenter,
  AlignRight,
  AlignJustify,
  List,
  ListOrdered,
  Undo,
  Redo,
  Table,
  Minus,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface EditorToolbarProps {
  editor: Editor;
  className?: string;
}

interface ToolbarButtonProps {
  onClick: () => void;
  isActive?: boolean;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
}

const ToolbarButton: React.FC<ToolbarButtonProps> = React.memo(
  ({ onClick, isActive = false, disabled = false, title, children }) => (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className={cn('h-8 w-8', isActive && 'bg-muted')}
      onClick={onClick}
      disabled={disabled}
      title={title}
    >
      {children}
    </Button>
  )
);

ToolbarButton.displayName = 'ToolbarButton';

type TextAlignment = 'left' | 'center' | 'right' | 'justify';

export const EditorToolbar: React.FC<EditorToolbarProps> = React.memo(
  ({ editor, className }) => {
    const toggleBold = useCallback(
      () => editor.chain().focus().toggleBold().run(),
      [editor]
    );
    const toggleItalic = useCallback(
      () => editor.chain().focus().toggleItalic().run(),
      [editor]
    );
    const toggleUnderline = useCallback(
      () => editor.chain().focus().toggleUnderline().run(),
      [editor]
    );
    const toggleStrike = useCallback(
      () => editor.chain().focus().toggleStrike().run(),
      [editor]
    );
    const toggleBulletList = useCallback(
      () => editor.chain().focus().toggleBulletList().run(),
      [editor]
    );
    const toggleOrderedList = useCallback(
      () => editor.chain().focus().toggleOrderedList().run(),
      [editor]
    );
    const setHorizontalRule = useCallback(
      () => editor.chain().focus().setHorizontalRule().run(),
      [editor]
    );
    const insertTable = useCallback(
      () =>
        editor
          .chain()
          .focus()
          .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
          .run(),
      [editor]
    );
    const handleUndo = useCallback(
      () => editor.chain().focus().undo().run(),
      [editor]
    );
    const handleRedo = useCallback(
      () => editor.chain().focus().redo().run(),
      [editor]
    );

    const setTextAlign = useCallback(
      (alignment: TextAlignment) => {
        editor.chain().focus().setTextAlign(alignment).run();
      },
      [editor]
    );

    const handleBlockTypeChange = useCallback(
      (value: string) => {
        switch (value) {
          case 'paragraph':
            editor.chain().focus().setParagraph().run();
            break;
          case 'heading1':
            editor.chain().focus().toggleHeading({ level: 1 }).run();
            break;
          case 'heading2':
            editor.chain().focus().toggleHeading({ level: 2 }).run();
            break;
          case 'heading3':
            editor.chain().focus().toggleHeading({ level: 3 }).run();
            break;
        }
      },
      [editor]
    );

    const getCurrentBlockType = useCallback((): string => {
      if (editor.isActive('heading', { level: 1 })) return 'heading1';
      if (editor.isActive('heading', { level: 2 })) return 'heading2';
      if (editor.isActive('heading', { level: 3 })) return 'heading3';
      return 'paragraph';
    }, [editor]);

    return (
      <div
        className={cn(
          'flex flex-wrap items-center gap-1 p-2 border-b bg-muted/50',
          className
        )}
      >
        <Select
          value={getCurrentBlockType()}
          onValueChange={handleBlockTypeChange}
        >
          <SelectTrigger className="w-[130px] h-8">
            <SelectValue placeholder="Parágrafo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="paragraph">Parágrafo</SelectItem>
            <SelectItem value="heading1">Título 1</SelectItem>
            <SelectItem value="heading2">Título 2</SelectItem>
            <SelectItem value="heading3">Título 3</SelectItem>
          </SelectContent>
        </Select>

        <Separator orientation="vertical" className="mx-1 h-6" />

        <ToolbarButton
          onClick={toggleBold}
          isActive={editor.isActive('bold')}
          title="Negrito (Ctrl+B)"
        >
          <Bold className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={toggleItalic}
          isActive={editor.isActive('italic')}
          title="Itálico (Ctrl+I)"
        >
          <Italic className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={toggleUnderline}
          isActive={editor.isActive('underline')}
          title="Sublinhado (Ctrl+U)"
        >
          <Underline className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={toggleStrike}
          isActive={editor.isActive('strike')}
          title="Tachado"
        >
          <Strikethrough className="h-4 w-4" />
        </ToolbarButton>

        <Separator orientation="vertical" className="mx-1 h-6" />

        <ToolbarButton
          onClick={() => setTextAlign('left')}
          isActive={editor.isActive({ textAlign: 'left' })}
          title="Alinhar à esquerda"
        >
          <AlignLeft className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => setTextAlign('center')}
          isActive={editor.isActive({ textAlign: 'center' })}
          title="Centralizar"
        >
          <AlignCenter className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => setTextAlign('right')}
          isActive={editor.isActive({ textAlign: 'right' })}
          title="Alinhar à direita"
        >
          <AlignRight className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => setTextAlign('justify')}
          isActive={editor.isActive({ textAlign: 'justify' })}
          title="Justificar"
        >
          <AlignJustify className="h-4 w-4" />
        </ToolbarButton>

        <Separator orientation="vertical" className="mx-1 h-6" />

        <ToolbarButton
          onClick={toggleBulletList}
          isActive={editor.isActive('bulletList')}
          title="Lista com marcadores"
        >
          <List className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={toggleOrderedList}
          isActive={editor.isActive('orderedList')}
          title="Lista numerada"
        >
          <ListOrdered className="h-4 w-4" />
        </ToolbarButton>

        <Separator orientation="vertical" className="mx-1 h-6" />

        <ToolbarButton onClick={setHorizontalRule} title="Linha horizontal">
          <Minus className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton onClick={insertTable} title="Inserir tabela">
          <Table className="h-4 w-4" />
        </ToolbarButton>

        <Separator orientation="vertical" className="mx-1 h-6" />

        <ToolbarButton
          onClick={handleUndo}
          disabled={!editor.can().undo()}
          title="Desfazer (Ctrl+Z)"
        >
          <Undo className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={handleRedo}
          disabled={!editor.can().redo()}
          title="Refazer (Ctrl+Y)"
        >
          <Redo className="h-4 w-4" />
        </ToolbarButton>
      </div>
    );
  }
);

EditorToolbar.displayName = 'EditorToolbar';
