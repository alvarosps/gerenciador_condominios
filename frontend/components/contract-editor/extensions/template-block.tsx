'use client';

import { Node, mergeAttributes } from '@tiptap/core';
import {
  NodeViewWrapper,
  NodeViewProps,
  ReactNodeViewRenderer,
} from '@tiptap/react';
import React from 'react';
import { cn } from '@/lib/utils';

type BlockType = 'if' | 'for' | 'endif' | 'endfor' | 'else' | 'elif';

interface TemplateBlockAttributes {
  blockType: BlockType;
  content: string;
}

const TemplateBlockView: React.FC<NodeViewProps> = ({ node }) => {
  const { blockType, content } = node.attrs as TemplateBlockAttributes;
  const displayText = content
    ? `{% ${blockType} ${content} %}`
    : `{% ${blockType} %}`;
  const isEndBlock = blockType === 'endif' || blockType === 'endfor';
  const isForBlock = blockType === 'for' || blockType === 'endfor';

  return (
    <NodeViewWrapper
      as="span"
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 mx-0.5',
        'rounded text-sm font-mono border select-none cursor-default',
        isForBlock
          ? 'bg-purple-100 text-purple-800 border-purple-200'
          : 'bg-amber-100 text-amber-800 border-amber-200',
        isEndBlock && 'opacity-75'
      )}
      contentEditable={false}
      data-template-block={blockType}
      data-content={content}
    >
      {displayText}
    </NodeViewWrapper>
  );
};

TemplateBlockView.displayName = 'TemplateBlockView';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    templateBlock: {
      insertTemplateBlock: (options: {
        blockType: BlockType;
        content?: string;
      }) => ReturnType;
    };
  }
}

/**
 * Tiptap extension for Jinja2 template blocks
 *
 * Renders {% if/for/endif/endfor %} as inline badges
 */
export const TemplateBlock = Node.create({
  name: 'templateBlock',
  group: 'inline',
  inline: true,
  atom: true,

  addAttributes() {
    return {
      blockType: {
        default: 'if',
        parseHTML: (element: HTMLElement) =>
          element.getAttribute('data-template-block'),
        renderHTML: (attributes: TemplateBlockAttributes) => ({
          'data-template-block': attributes.blockType,
        }),
      },
      content: {
        default: '',
        parseHTML: (element: HTMLElement) =>
          element.getAttribute('data-content') ?? '',
        renderHTML: (attributes: TemplateBlockAttributes) => {
          if (!attributes.content) return {};
          return { 'data-content': attributes.content };
        },
      },
    };
  },

  parseHTML() {
    return [{ tag: 'span[data-template-block]' }];
  },

  renderHTML({ HTMLAttributes }) {
    const attrs = HTMLAttributes as TemplateBlockAttributes &
      Record<string, unknown>;
    const displayText = attrs.content
      ? `{% ${attrs.blockType} ${attrs.content} %}`
      : `{% ${attrs.blockType} %}`;

    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        class: 'template-block',
        contenteditable: 'false',
      }),
      displayText,
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(TemplateBlockView);
  },

  addCommands() {
    return {
      insertTemplateBlock:
        (options: { blockType: BlockType; content?: string }) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: {
              blockType: options.blockType,
              content: options.content ?? '',
            },
          });
        },
    };
  },
});
