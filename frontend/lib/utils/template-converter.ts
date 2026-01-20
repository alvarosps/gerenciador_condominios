/**
 * Template Converter Utility
 *
 * Converts between Jinja2 template syntax and WYSIWYG-compatible HTML.
 * Used by the WYSIWYG editor to display template variables as styled badges
 * while preserving the original Jinja2 syntax for saving.
 *
 * Also handles extraction of body content from full HTML documents since
 * Tiptap only works with content fragments, not full HTML documents.
 */

const JINJA_VARIABLE_REGEX = /\{\{\s*([^}|]+)(?:\s*\|\s*([^}]+))?\s*\}\}/g;
const JINJA_BLOCK_REGEX =
  /\{%\s*(if|for|endif|endfor|else|elif)\s*([^%]*)\s*%\}/g;

// Regex to extract body content from full HTML document
const BODY_CONTENT_REGEX = /<body[^>]*>([\s\S]*)<\/body>/i;
const FULL_DOCUMENT_REGEX = /<!DOCTYPE\s+html/i;

// Self-closing page break regex (handles <div class="page-break" />)
const SELF_CLOSING_PAGE_BREAK_REGEX = /<div\s+class="page-break"\s*\/>/gi;

// Regex to match tables containing Jinja blocks (for/endfor, if/endif)
const TABLE_WITH_JINJA_REGEX = /<table[^>]*>[\s\S]*?\{%[\s\S]*?<\/table>/gi;

// Regex to match lists (ul/ol) where Jinja block appears at the START (after whitespace)
// This prevents matching static HTML lists that happen to appear before Jinja-templated lists
const LIST_WITH_JINJA_REGEX = /<(ul|ol)[^>]*>\s*\{%[\s\S]*?<\/\1>/gi;

// Regex to match signature section with custom CSS classes
const SIGNATURE_SECTION_REGEX = /<div\s+class="signature-section"[^>]*>[\s\S]*?<\/div>\s*(?=<\/body>|$)/gi;

function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (char) => map[char] ?? char);
}

function unescapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&amp;': '&',
    '&lt;': '<',
    '&gt;': '>',
    '&quot;': '"',
    '&#039;': "'",
  };
  return text.replace(
    /&(amp|lt|gt|quot|#039);/g,
    (entity) => map[entity] ?? entity
  );
}

/**
 * Checks if the HTML is a full document (has DOCTYPE)
 */
export function isFullHtmlDocument(html: string): boolean {
  return FULL_DOCUMENT_REGEX.test(html);
}

/**
 * Extracts just the body content from a full HTML document.
 * Returns the original HTML if it's not a full document.
 */
export function extractBodyContent(html: string): string {
  if (!isFullHtmlDocument(html)) {
    return html;
  }

  const match = BODY_CONTENT_REGEX.exec(html);
  if (match && match[1]) {
    return match[1].trim();
  }

  return html;
}

/**
 * Reconstructs a full HTML document by injecting body content back
 * into the original document structure.
 */
export function reconstructFullDocument(
  originalDocument: string,
  bodyContent: string
): string {
  if (!isFullHtmlDocument(originalDocument)) {
    return bodyContent;
  }

  return originalDocument.replace(BODY_CONTENT_REGEX, `<body>\n${bodyContent}\n  </body>`);
}

/**
 * Converts Jinja2 template to WYSIWYG-compatible HTML
 *
 * Transforms:
 * - {{ variable }} -> <span data-template-variable="variable">{{ variable }}</span>
 * - {{ variable | filter }} -> <span data-template-variable="variable" data-filter="filter">{{ variable | filter }}</span>
 * - {% if/for %} -> <span data-template-block="if|for" data-content="...">{% block %}</span>
 * - <div class="page-break" /> -> <div class="page-break"></div>
 * - Tables with Jinja blocks -> wrapped as atomic non-editable content
 */
export function jinjaToWysiwyg(html: string): string {
  let result = html;

  // Normalize self-closing page breaks to proper div tags (for Tiptap parsing)
  result = result.replace(
    SELF_CLOSING_PAGE_BREAK_REGEX,
    '<div class="page-break"></div>'
  );

  // CRITICAL: Extract tables with Jinja blocks and wrap them as atomic content
  // This prevents invalid HTML (spans can't be direct children of tables)
  const tablesWithJinja: string[] = [];
  result = result.replace(TABLE_WITH_JINJA_REGEX, (match) => {
    const index = tablesWithJinja.length;
    tablesWithJinja.push(match);
    return `<!--TABLE_PLACEHOLDER_${index}-->`;
  });

  // Extract lists with Jinja blocks (for loops in ul/ol)
  // This prevents spans appearing as list items
  const listsWithJinja: string[] = [];
  result = result.replace(LIST_WITH_JINJA_REGEX, (match) => {
    const index = listsWithJinja.length;
    listsWithJinja.push(match);
    return `<!--LIST_PLACEHOLDER_${index}-->`;
  });

  // Extract signature section with custom CSS classes
  const signatureSections: string[] = [];
  result = result.replace(SIGNATURE_SECTION_REGEX, (match) => {
    const index = signatureSections.length;
    signatureSections.push(match);
    return `<!--SIGNATURE_PLACEHOLDER_${index}-->`;
  });

  // Convert {{ variable }} to span nodes (outside of protected blocks)
  result = result.replace(
    JINJA_VARIABLE_REGEX,
    (match, variable: string, filter?: string) => {
      const trimmedVariable = variable.trim();
      const trimmedFilter = filter?.trim();
      const filterAttr = trimmedFilter
        ? ` data-filter="${escapeHtml(trimmedFilter)}"`
        : '';
      return `<span data-template-variable="${escapeHtml(trimmedVariable)}"${filterAttr} contenteditable="false">${escapeHtml(match)}</span>`;
    }
  );

  // Convert {% block %} to span nodes (outside of tables with Jinja)
  result = result.replace(
    JINJA_BLOCK_REGEX,
    (match, blockType: string, content: string) => {
      const trimmedContent = content.trim();
      return `<span data-template-block="${blockType}" data-content="${escapeHtml(trimmedContent)}" contenteditable="false">${escapeHtml(match)}</span>`;
    }
  );

  // Restore tables with Jinja as atomic non-editable blocks
  // These tables are wrapped in a div that Tiptap treats as a single unit
  // Content is stored in data-table-content attribute (URL-encoded) to survive Tiptap's getHTML()
  tablesWithJinja.forEach((tableHtml, index) => {
    const encodedContent = encodeURIComponent(tableHtml);
    const wrappedTable = `<div data-template-table="true" data-table-content="${encodedContent}" contenteditable="false" class="template-table-wrapper">${tableHtml}</div>`;
    result = result.replace(`<!--TABLE_PLACEHOLDER_${index}-->`, wrappedTable);
  });

  // Restore lists with Jinja as atomic non-editable blocks
  listsWithJinja.forEach((listHtml, index) => {
    const encodedContent = encodeURIComponent(listHtml);
    const wrappedList = `<div data-template-list="true" data-list-content="${encodedContent}" contenteditable="false" class="template-list-wrapper">${listHtml}</div>`;
    result = result.replace(`<!--LIST_PLACEHOLDER_${index}-->`, wrappedList);
  });

  // Restore signature sections as atomic non-editable blocks
  signatureSections.forEach((sectionHtml, index) => {
    const encodedContent = encodeURIComponent(sectionHtml);
    const wrappedSection = `<div data-template-signature="true" data-signature-content="${encodedContent}" contenteditable="false" class="template-signature-wrapper">${sectionHtml}</div>`;
    result = result.replace(`<!--SIGNATURE_PLACEHOLDER_${index}-->`, wrappedSection);
  });

  return result;
}

/**
 * Converts WYSIWYG HTML back to Jinja2 template syntax
 *
 * Transforms:
 * - <span data-template-variable="variable">...</span> -> {{ variable }}
 * - <span data-template-variable="variable" data-filter="filter">...</span> -> {{ variable | filter }}
 * - <span data-template-block="if" data-content="...">...</span> -> {% if ... %}
 * - <div data-template-table>...</div> -> unwrapped table with original Jinja
 */
export function wysiwygToJinja(html: string): string {
  // Guard for SSR - DOMParser only available in browser
  if (typeof window === 'undefined') return html;

  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');

  // Process template tables first (unwrap them, preserving inner content)
  const templateTables = doc.querySelectorAll('[data-template-table]');
  templateTables.forEach((el) => {
    // Get table content from data attribute (URL-encoded) to avoid escaping issues
    const encodedContent = el.getAttribute('data-table-content');
    const tableContent = encodedContent
      ? decodeURIComponent(encodedContent)
      : el.innerHTML; // Fallback to innerHTML if attribute missing
    const fragment = doc.createRange().createContextualFragment(tableContent);
    el.parentNode?.replaceChild(fragment, el);
  });

  // Process template lists (unwrap them, preserving inner content)
  const templateLists = doc.querySelectorAll('[data-template-list]');
  templateLists.forEach((el) => {
    const encodedContent = el.getAttribute('data-list-content');
    const listContent = encodedContent
      ? decodeURIComponent(encodedContent)
      : el.innerHTML;
    const fragment = doc.createRange().createContextualFragment(listContent);
    el.parentNode?.replaceChild(fragment, el);
  });

  // Process template signature sections (unwrap them, preserving inner content)
  const templateSignatures = doc.querySelectorAll('[data-template-signature]');
  templateSignatures.forEach((el) => {
    const encodedContent = el.getAttribute('data-signature-content');
    const signatureContent = encodedContent
      ? decodeURIComponent(encodedContent)
      : el.innerHTML;
    const fragment = doc.createRange().createContextualFragment(signatureContent);
    el.parentNode?.replaceChild(fragment, el);
  });

  // Process template variables
  const variables = doc.querySelectorAll('[data-template-variable]');
  variables.forEach((el) => {
    const variable = el.getAttribute('data-template-variable');
    const filter = el.getAttribute('data-filter');

    if (variable) {
      const replacement = filter
        ? `{{ ${unescapeHtml(variable)} | ${unescapeHtml(filter)} }}`
        : `{{ ${unescapeHtml(variable)} }}`;

      const textNode = doc.createTextNode(replacement);
      el.parentNode?.replaceChild(textNode, el);
    }
  });

  // Process template blocks
  const blocks = doc.querySelectorAll('[data-template-block]');
  blocks.forEach((el) => {
    const blockType = el.getAttribute('data-template-block');
    const content = el.getAttribute('data-content') ?? '';

    if (blockType) {
      const replacement = content
        ? `{% ${blockType} ${unescapeHtml(content)} %}`
        : `{% ${blockType} %}`;

      const textNode = doc.createTextNode(replacement);
      el.parentNode?.replaceChild(textNode, el);
    }
  });

  return doc.body.innerHTML;
}
