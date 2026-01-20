'use client';

import { Node, mergeAttributes } from '@tiptap/core';
import {
  NodeViewWrapper,
  NodeViewProps,
  ReactNodeViewRenderer,
} from '@tiptap/react';
import React from 'react';
import { cn } from '@/lib/utils';

interface TemplateVariableAttributes {
  variable: string;
  filter: string | null;
}

const TemplateVariableView: React.FC<NodeViewProps> = ({ node }) => {
  const { variable, filter } = node.attrs as TemplateVariableAttributes;
  const displayText = filter
    ? `{{ ${variable} | ${filter} }}`
    : `{{ ${variable} }}`;

  return (
    <NodeViewWrapper
      as="span"
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 mx-0.5',
        'bg-blue-100 text-blue-800 rounded text-sm font-mono',
        'border border-blue-200 select-none cursor-default'
      )}
      contentEditable={false}
      data-template-variable={variable}
      data-filter={filter}
    >
      {displayText}
    </NodeViewWrapper>
  );
};

TemplateVariableView.displayName = 'TemplateVariableView';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    templateVariable: {
      insertTemplateVariable: (options: {
        variable: string;
        filter?: string;
      }) => ReturnType;
    };
  }
}

/**
 * Tiptap extension for Jinja2 template variables
 *
 * Renders {{ variable }} and {{ variable | filter }} as inline badges
 */
export const TemplateVariable = Node.create({
  name: 'templateVariable',
  group: 'inline',
  inline: true,
  atom: true,

  addAttributes() {
    return {
      variable: {
        default: '',
        parseHTML: (element: HTMLElement) =>
          element.getAttribute('data-template-variable'),
        renderHTML: (attributes: TemplateVariableAttributes) => ({
          'data-template-variable': attributes.variable,
        }),
      },
      filter: {
        default: null,
        parseHTML: (element: HTMLElement) =>
          element.getAttribute('data-filter'),
        renderHTML: (attributes: TemplateVariableAttributes) => {
          if (!attributes.filter) return {};
          return { 'data-filter': attributes.filter };
        },
      },
    };
  },

  parseHTML() {
    return [{ tag: 'span[data-template-variable]' }];
  },

  renderHTML({ HTMLAttributes }) {
    const attrs = HTMLAttributes as TemplateVariableAttributes &
      Record<string, unknown>;
    const displayText = attrs.filter
      ? `{{ ${attrs.variable} | ${attrs.filter} }}`
      : `{{ ${attrs.variable} }}`;

    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        class: 'template-variable',
        contenteditable: 'false',
      }),
      displayText,
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(TemplateVariableView);
  },

  addCommands() {
    return {
      insertTemplateVariable:
        (options: { variable: string; filter?: string }) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: { variable: options.variable, filter: options.filter ?? null },
          });
        },
    };
  },
});
