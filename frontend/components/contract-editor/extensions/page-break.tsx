'use client';

import { Node, mergeAttributes } from '@tiptap/core';
import {
  NodeViewWrapper,
  NodeViewProps,
  ReactNodeViewRenderer,
} from '@tiptap/react';
import React from 'react';
import { cn } from '@/lib/utils';

/**
 * Visual representation of page break in the editor
 */
const PageBreakView: React.FC<NodeViewProps> = () => {
  return (
    <NodeViewWrapper
      as="div"
      className={cn(
        'page-break-node',
        'my-4 py-2 border-t-2 border-dashed border-gray-400',
        'flex items-center justify-center',
        'select-none cursor-default'
      )}
      contentEditable={false}
      data-type="pageBreak"
    >
      <span className="px-3 py-1 text-xs text-gray-500 bg-gray-100 rounded-full uppercase tracking-wide">
        Quebra de Página
      </span>
    </NodeViewWrapper>
  );
};

PageBreakView.displayName = 'PageBreakView';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    pageBreak: {
      insertPageBreak: () => ReturnType;
    };
  }
}

/**
 * Tiptap extension for page breaks
 *
 * Parses <div class="page-break"> elements from contract template
 * Renders as visual separator in editor
 * Outputs back as <div class="page-break"></div> for PDF generation
 */
export const PageBreak = Node.create({
  name: 'pageBreak',
  group: 'block',
  atom: true, // Non-editable, treated as single unit

  parseHTML() {
    return [
      // Match <div class="page-break"> (with or without self-closing)
      { tag: 'div.page-break' },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        class: 'page-break',
      }),
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(PageBreakView);
  },

  addCommands() {
    return {
      insertPageBreak:
        () =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
          });
        },
    };
  },
});
