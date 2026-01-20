'use client';

import React, { useEffect, useMemo, useRef } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import { Table } from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import Placeholder from '@tiptap/extension-placeholder';
import { cn } from '@/lib/utils';
import { EditorToolbar } from './editor-toolbar';
import { VariableInserter } from './variable-inserter';
import { TemplateVariable, TemplateBlock, PageBreak, TemplateTable, TemplateList, TemplateSignature } from './extensions';
import {
  jinjaToWysiwyg,
  wysiwygToJinja,
  extractBodyContent,
  reconstructFullDocument,
  isFullHtmlDocument,
} from '@/lib/utils/template-converter';

interface WysiwygEditorProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  placeholder?: string;
  disabled?: boolean;
}

/**
 * WYSIWYG Editor for Contract Templates
 *
 * Features:
 * - Rich text formatting (bold, italic, underline, etc.)
 * - Text alignment
 * - Tables
 * - Lists
 * - Custom Jinja2 template variable nodes
 * - Custom Jinja2 block nodes
 * - Page break visualization
 *
 * CRITICAL: Uses immediatelyRender: false for Next.js SSR compatibility
 * PERFORMANCE: Uses shouldRerenderOnTransaction: false to prevent unnecessary re-renders
 */
export const WysiwygEditor: React.FC<WysiwygEditorProps> = React.memo(
  ({
    value,
    onChange,
    className,
    placeholder = 'Digite o conteúdo do contrato aqui...',
    disabled = false,
  }) => {
    // === REFS FOR SYNC CONTROL ===
    // Store original full document for reconstruction
    const originalDocumentRef = useRef<string>('');
    // Track if input is full HTML document
    const isFullDocRef = useRef<boolean>(false);
    // Prevent stale closure - ALWAYS use ref for callbacks
    const onChangeRef = useRef(onChange);
    // Track last synced value to prevent redundant updates
    const lastSyncedValueRef = useRef<string>('');
    // Guard against programmatic update feedback loops
    const isSyncingRef = useRef<boolean>(false);
    // Track initialization state
    const isInitializedRef = useRef<boolean>(false);

    // Keep onChangeRef up-to-date (critical for avoiding stale closures)
    useEffect(() => {
      onChangeRef.current = onChange;
    }, [onChange]);

    const extensions = useMemo(
      () => [
        StarterKit.configure({
          heading: { levels: [1, 2, 3] },
        }),
        Underline,
        TextAlign.configure({
          types: ['heading', 'paragraph'],
          alignments: ['left', 'center', 'right', 'justify'],
        }),
        Table.configure({
          resizable: true,
          HTMLAttributes: { class: 'wysiwyg-table' },
        }),
        TableRow,
        TableCell,
        TableHeader,
        Placeholder.configure({ placeholder }),
        TemplateVariable,
        TemplateBlock,
        PageBreak,
        TemplateTable,
        TemplateList,
        TemplateSignature,
      ],
      [placeholder]
    );

    const editor = useEditor({
      extensions,
      immediatelyRender: false, // CRITICAL: Required for Next.js SSR
      shouldRerenderOnTransaction: false, // PERFORMANCE: Prevents unnecessary re-renders
      editable: !disabled,
      editorProps: {
        attributes: {
          class: cn(
            'prose prose-sm max-w-none focus:outline-none',
            disabled && 'opacity-50 cursor-not-allowed'
          ),
        },
      },
      onUpdate: ({ editor: currentEditor }) => {
        // Skip during initialization or programmatic sync
        if (!isInitializedRef.current || isSyncingRef.current) {
          return;
        }

        const html = currentEditor.getHTML();
        const jinja = wysiwygToJinja(html);

        // Reconstruct full document if needed
        let outputValue: string;
        if (isFullDocRef.current && originalDocumentRef.current) {
          outputValue = reconstructFullDocument(originalDocumentRef.current, jinja);
        } else {
          outputValue = jinja;
        }

        // Update tracking ref and call onChange via ref (prevents stale closure)
        lastSyncedValueRef.current = outputValue;
        onChangeRef.current(outputValue);
      },
    });

    // Sync external value changes to editor
    useEffect(() => {
      if (!editor) return;

      // Skip if this is the same value we just emitted (prevents loops)
      if (value === lastSyncedValueRef.current) {
        return;
      }

      // Check if this is a full HTML document
      const isFullDoc = isFullHtmlDocument(value);
      isFullDocRef.current = isFullDoc;

      // Store original document for reconstruction (only on initial load or external change)
      if (isFullDoc) {
        originalDocumentRef.current = value;
      }

      // Extract body content and convert to WYSIWYG format
      const bodyContent = extractBodyContent(value);
      const wysiwygHtml = jinjaToWysiwyg(bodyContent);

      // Set content synchronously with sync guard
      isSyncingRef.current = true;
      editor.commands.setContent(wysiwygHtml, { emitUpdate: false });
      isSyncingRef.current = false;

      // Mark as initialized and track synced value
      isInitializedRef.current = true;
      lastSyncedValueRef.current = value;
    }, [editor, value]);

    // Handle disabled state changes with sync guard
    useEffect(() => {
      if (!editor) return;

      // Guard setEditable to prevent unexpected update emissions
      isSyncingRef.current = true;
      editor.setEditable(!disabled);
      isSyncingRef.current = false;
    }, [editor, disabled]);

    // Loading state for SSR hydration
    if (!editor) {
      return (
        <div className={cn('border rounded-md bg-background flex flex-col', className)}>
          <div className="h-10 border-b bg-muted/50 animate-pulse flex-shrink-0" />
          <div className="flex-1 p-4 overflow-y-auto">
            <div className="space-y-2">
              <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
              <div className="h-4 bg-muted rounded animate-pulse w-1/2" />
              <div className="h-4 bg-muted rounded animate-pulse w-2/3" />
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className={cn('border rounded-md bg-background flex flex-col', className)}>
        <div className="flex items-center justify-between border-b flex-shrink-0">
          <EditorToolbar editor={editor} />
          <div className="pr-2">
            <VariableInserter editor={editor} />
          </div>
        </div>
        <EditorContent editor={editor} className="wysiwyg-editor-content" />
      </div>
    );
  }
);

WysiwygEditor.displayName = 'WysiwygEditor';
