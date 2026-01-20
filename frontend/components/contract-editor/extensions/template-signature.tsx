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
 * Visual representation of a signature section in the editor.
 * The signature section uses custom CSS classes for layout that Tiptap
 * doesn't understand, so we render it as a non-editable block.
 *
 * Security Note: Uses dangerouslySetInnerHTML to render content. This is safe
 * because the content originates from the user's own contract template stored
 * in the backend database, not from untrusted external input.
 */
const TemplateSignatureView: React.FC<NodeViewProps> = ({ node }) => {
  return (
    <NodeViewWrapper
      as="div"
      className={cn(
        'template-signature-wrapper',
        'my-4 p-3 border-2 border-dashed border-emerald-400 rounded-lg',
        'bg-emerald-50 dark:bg-emerald-950/20',
        'select-none'
      )}
      contentEditable={false}
      data-type="templateSignature"
    >
      <div className="text-xs text-emerald-700 dark:text-emerald-400 mb-2 font-medium uppercase tracking-wide flex items-center gap-1">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="w-4 h-4"
        >
          <path d="M3.5 11.5a.5.5 0 01.5-.5h9a.5.5 0 010 1h-9a.5.5 0 01-.5-.5zm0-4a.5.5 0 01.5-.5h9a.5.5 0 010 1h-9a.5.5 0 01-.5-.5zm0 8a.5.5 0 01.5-.5h9a.5.5 0 010 1h-9a.5.5 0 01-.5-.5z" />
          <path d="M15.854 3.146a.5.5 0 010 .708l-7 7a.5.5 0 01-.708 0l-3-3a.5.5 0 11.708-.708L8.5 9.793l6.646-6.647a.5.5 0 01.708 0z" />
        </svg>
        Seção de Assinaturas (somente leitura)
      </div>
      {/* Content is from user's own contract template, not untrusted input */}
      <div
        className="template-signature-content"
        dangerouslySetInnerHTML={{ __html: node.attrs.content || '' }}
      />
    </NodeViewWrapper>
  );
};

TemplateSignatureView.displayName = 'TemplateSignatureView';

/**
 * Tiptap extension for signature sections with custom CSS layout.
 *
 * The signature section uses custom CSS classes (.signature-section, .row, .column, etc.)
 * that Tiptap doesn't preserve. We render the entire section as an atomic block
 * to maintain the proper layout structure.
 */
export const TemplateSignature = Node.create({
  name: 'templateSignature',
  group: 'block',
  atom: true, // Non-editable, treated as single unit

  addAttributes() {
    return {
      content: {
        default: '',
        // Parse from URL-encoded data attribute
        parseHTML: (element) => {
          const encoded = element.getAttribute('data-signature-content');
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
            'data-signature-content': encodeURIComponent(attributes.content),
          };
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-template-signature]',
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        'data-template-signature': 'true',
        contenteditable: 'false',
        class: 'template-signature-wrapper',
      }),
      0,
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(TemplateSignatureView);
  },
});
