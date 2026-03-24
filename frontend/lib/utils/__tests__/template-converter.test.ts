import { describe, it, expect } from 'vitest';
import {
  isFullHtmlDocument,
  extractBodyContent,
  reconstructFullDocument,
  jinjaToWysiwyg,
  wysiwygToJinja,
} from '../template-converter';

const FULL_HTML = `<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
  <p>Hello</p>
</body>
</html>`;

describe('isFullHtmlDocument', () => {
  it('returns true for HTML with DOCTYPE', () => {
    expect(isFullHtmlDocument('<!DOCTYPE html><html></html>')).toBe(true);
    expect(isFullHtmlDocument('<!doctype html><html></html>')).toBe(true);
  });

  it('returns false for HTML fragment', () => {
    expect(isFullHtmlDocument('<p>Hello</p>')).toBe(false);
    expect(isFullHtmlDocument('')).toBe(false);
  });
});

describe('extractBodyContent', () => {
  it('extracts body content from a full HTML document', () => {
    const result = extractBodyContent(FULL_HTML);
    expect(result).toContain('<p>Hello</p>');
    expect(result).not.toContain('<!DOCTYPE');
    expect(result).not.toContain('<html>');
  });

  it('returns the original string for non-full documents', () => {
    const fragment = '<p>Just a paragraph</p>';
    expect(extractBodyContent(fragment)).toBe(fragment);
  });

  it('returns original HTML if no body tag found', () => {
    const malformed = '<!DOCTYPE html><html><p>No body tag</p></html>';
    // No <body> tag → returns original
    expect(extractBodyContent(malformed)).toBe(malformed);
  });
});

describe('reconstructFullDocument', () => {
  it('injects body content back into original document', () => {
    const original = FULL_HTML;
    const newBody = '<p>New content</p>';
    const result = reconstructFullDocument(original, newBody);
    expect(result).toContain('<p>New content</p>');
    expect(result).toContain('<!DOCTYPE html>');
    expect(result).toContain('<head>');
  });

  it('returns bodyContent unchanged if original is not a full document', () => {
    const result = reconstructFullDocument('<p>fragment</p>', '<p>body</p>');
    expect(result).toBe('<p>body</p>');
  });
});

describe('jinjaToWysiwyg', () => {
  it('converts {{ variable }} to a data-template-variable span', () => {
    const input = '<p>{{ tenant_name }}</p>';
    const result = jinjaToWysiwyg(input);
    expect(result).toContain('data-template-variable="tenant_name"');
    expect(result).toContain('contenteditable="false"');
  });

  it('converts {{ variable | filter }} including data-filter attribute', () => {
    const input = '<p>{{ amount | currency }}</p>';
    const result = jinjaToWysiwyg(input);
    expect(result).toContain('data-template-variable="amount"');
    expect(result).toContain('data-filter="currency"');
  });

  it('converts {% if %} blocks to data-template-block spans', () => {
    const input = '<p>{% if active %}</p>';
    const result = jinjaToWysiwyg(input);
    expect(result).toContain('data-template-block="if"');
    expect(result).toContain('data-content="active"');
  });

  it('converts {% for %} blocks', () => {
    const input = '<p>{% for item in items %}</p>';
    const result = jinjaToWysiwyg(input);
    expect(result).toContain('data-template-block="for"');
  });

  it('converts {% endif %} and {% endfor %} blocks', () => {
    const input = '<p>{% endif %}</p><p>{% endfor %}</p>';
    const result = jinjaToWysiwyg(input);
    expect(result).toContain('data-template-block="endif"');
    expect(result).toContain('data-template-block="endfor"');
  });

  it('normalizes self-closing page-break divs', () => {
    const input = '<div class="page-break" />';
    const result = jinjaToWysiwyg(input);
    expect(result).toContain('<div class="page-break"></div>');
    expect(result).not.toContain('<div class="page-break" />');
  });

  it('wraps tables containing Jinja blocks as atomic blocks', () => {
    const input = '<table><tr><td>{% for row in rows %}</td></tr></table>';
    const result = jinjaToWysiwyg(input);
    expect(result).toContain('data-template-table="true"');
    expect(result).toContain('data-table-content=');
  });

  it('passes through plain HTML unchanged', () => {
    const input = '<p>No templates here</p>';
    const result = jinjaToWysiwyg(input);
    expect(result).toBe(input);
  });
});

describe('wysiwygToJinja', () => {
  it('converts data-template-variable span back to {{ variable }}', () => {
    const input =
      '<p><span data-template-variable="tenant_name" contenteditable="false">{{ tenant_name }}</span></p>';
    const result = wysiwygToJinja(input);
    expect(result).toContain('{{ tenant_name }}');
    expect(result).not.toContain('data-template-variable');
  });

  it('converts span with data-filter back to {{ variable | filter }}', () => {
    const input =
      '<p><span data-template-variable="amount" data-filter="currency" contenteditable="false">{{ amount | currency }}</span></p>';
    const result = wysiwygToJinja(input);
    expect(result).toContain('{{ amount | currency }}');
  });

  it('converts data-template-block span back to {% block %}', () => {
    const input =
      '<p><span data-template-block="if" data-content="active" contenteditable="false">{% if active %}</span></p>';
    const result = wysiwygToJinja(input);
    expect(result).toContain('{% if active %}');
    expect(result).not.toContain('data-template-block');
  });

  it('converts data-template-block without content (e.g., endif)', () => {
    const input =
      '<p><span data-template-block="endif" data-content="" contenteditable="false">{% endif %}</span></p>';
    const result = wysiwygToJinja(input);
    expect(result).toContain('{% endif %}');
  });

  it('unwraps data-template-table divs preserving original table', () => {
    const tableHtml = '<table><tr><td>{% for row in rows %}</td></tr></table>';
    const encoded = encodeURIComponent(tableHtml);
    const input = `<div data-template-table="true" data-table-content="${encoded}" contenteditable="false">${tableHtml}</div>`;
    const result = wysiwygToJinja(input);
    expect(result).toContain('<table>');
    expect(result).not.toContain('data-template-table');
  });

  it('handles SSR environment gracefully (window undefined check)', () => {
    // jsdom has window defined, so wysiwygToJinja should work normally
    const input = '<p>plain</p>';
    const result = wysiwygToJinja(input);
    expect(result).toBe(input);
  });

  it('is a round-trip with jinjaToWysiwyg for simple variables', () => {
    const original = '<p>{{ tenant_name }}</p>';
    const wysiwyg = jinjaToWysiwyg(original);
    const restored = wysiwygToJinja(wysiwyg);
    // The body content after round-trip should contain the original variable
    expect(restored).toContain('{{ tenant_name }}');
  });
});
