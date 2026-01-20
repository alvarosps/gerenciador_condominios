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
 * Visual representation of a template table with Jinja loops in the editor.
 * These tables are rendered as non-editable blocks to preserve their structure.
 *
 * Note: Uses dangerouslySetInnerHTML to render table content. This is safe here
 * because the content originates from the user's own contract template stored
 * in the backend, not from untrusted external input.
 */
const TemplateTableView: React.FC<NodeViewProps> = ({ node }) => {
  return (
    <NodeViewWrapper
      as="div"
      className={cn(
        'template-table-wrapper',
        'my-4 p-2 border-2 border-dashed border-purple-300 rounded-lg',
        'bg-purple-50 dark:bg-purple-950/20',
        'select-none'
      )}
      contentEditable={false}
      data-type="templateTable"
    >
      <div className="text-xs text-purple-600 dark:text-purple-400 mb-2 font-medium uppercase tracking-wide flex items-center gap-1">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="w-4 h-4"
        >
          <path
            fillRule="evenodd"
            d="M.99 5.24A2.25 2.25 0 013.25 3h13.5A2.25 2.25 0 0119 5.25l.01 9.5A2.25 2.25 0 0116.76 17H3.26A2.25 2.25 0 011 14.76l-.01-9.52zm8.26 9.52v-4.5H4.75v4.5h4.5zm.75-4.5v4.5h4.5v-4.5h-4.5zm4.5-.75H10v-4.5h4.5v4.5zm.75-4.5v4.5h1v-4.5h-1zm-6-3.25h-4.5v3.25h4.5v-3.25z"
            clipRule="evenodd"
          />
        </svg>
        Tabela com Loop (somente leitura)
      </div>
      {/* Content is from user's own contract template, not untrusted input */}
      <div
        className="template-table-content prose prose-sm max-w-none"
        dangerouslySetInnerHTML={{ __html: node.attrs.content || '' }}
      />
    </NodeViewWrapper>
  );
};

TemplateTableView.displayName = 'TemplateTableView';

/**
 * Tiptap extension for template tables containing Jinja loops.
 *
 * These tables need special handling because Jinja {% for %} blocks
 * between <tr> elements would create invalid HTML if converted to spans.
 * Instead, we render the entire table as an atomic, non-editable block.
 */
export const TemplateTable = Node.create({
  name: 'templateTable',
  group: 'block',
  atom: true, // Non-editable, treated as single unit

  addAttributes() {
    return {
      content: {
        default: '',
        // Parse from URL-encoded data attribute
        parseHTML: (element) => {
          const encoded = element.getAttribute('data-table-content');
          if (encoded) {
            try {
              return decodeURIComponent(encoded);
            } catch {
              return element.innerHTML;
            }
          }
          return element.innerHTML;
        },
        // Render as URL-encoded data attribute
        renderHTML: (attributes) => {
          if (!attributes.content) return {};
          return {
            'data-table-content': encodeURIComponent(attributes.content),
          };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-template-table]',
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        'data-template-table': 'true',
        contenteditable: 'false',
        class: 'template-table-wrapper',
      }),
      // Empty content - actual table HTML stored in data-table-content attribute
      0,
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(TemplateTableView);
  },
});
