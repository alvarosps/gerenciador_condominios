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
 * Visual representation of a template list with Jinja loops in the editor.
 * These lists are rendered as non-editable blocks to preserve their structure.
 *
 * Security Note: Uses dangerouslySetInnerHTML to render list content. This is safe
 * because the content originates from the user's own contract template stored
 * in the backend database, not from untrusted external input.
 */
const TemplateListView: React.FC<NodeViewProps> = ({ node }) => {
  return (
    <NodeViewWrapper
      as="div"
      className={cn(
        'template-list-wrapper',
        'my-4 p-3 border-2 border-dashed border-amber-400 rounded-lg',
        'bg-amber-50 dark:bg-amber-950/20',
        'select-none'
      )}
      contentEditable={false}
      data-type="templateList"
    >
      <div className="text-xs text-amber-700 dark:text-amber-400 mb-2 font-medium uppercase tracking-wide flex items-center gap-1">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="w-4 h-4"
        >
          <path
            fillRule="evenodd"
            d="M6 4.75A.75.75 0 016.75 4h10.5a.75.75 0 010 1.5H6.75A.75.75 0 016 4.75zM6 10a.75.75 0 01.75-.75h10.5a.75.75 0 010 1.5H6.75A.75.75 0 016 10zm0 5.25a.75.75 0 01.75-.75h10.5a.75.75 0 010 1.5H6.75a.75.75 0 01-.75-.75zM1.99 4.75a1 1 0 011-1H3a1 1 0 011 1v.01a1 1 0 01-1 1h-.01a1 1 0 01-1-1v-.01zM1.99 15.25a1 1 0 011-1H3a1 1 0 011 1v.01a1 1 0 01-1 1h-.01a1 1 0 01-1-1v-.01zM1.99 10a1 1 0 011-1H3a1 1 0 011 1v.01a1 1 0 01-1 1h-.01a1 1 0 01-1-1V10z"
            clipRule="evenodd"
          />
        </svg>
        Lista com Loop (somente leitura)
      </div>
      {/* Content is from user's own contract template, not untrusted input */}
      <div
        className="template-list-content prose prose-sm max-w-none"
        dangerouslySetInnerHTML={{ __html: node.attrs.content || '' }}
      />
    </NodeViewWrapper>
  );
};

TemplateListView.displayName = 'TemplateListView';

/**
 * Tiptap extension for template lists containing Jinja loops.
 *
 * These lists need special handling because Jinja {% for %} blocks
 * at the list level would create invalid HTML if converted to spans.
 * Instead, we render the entire list as an atomic, non-editable block.
 */
export const TemplateList = Node.create({
  name: 'templateList',
  group: 'block',
  atom: true, // Non-editable, treated as single unit

  addAttributes() {
    return {
      content: {
        default: '',
        // Parse from URL-encoded data attribute
        parseHTML: (element) => {
          const encoded = element.getAttribute('data-list-content');
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
            'data-list-content': encodeURIComponent(attributes.content),
          };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-template-list]',
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        'data-template-list': 'true',
        contenteditable: 'false',
        class: 'template-list-wrapper',
      }),
      0,
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(TemplateListView);
  },
});
