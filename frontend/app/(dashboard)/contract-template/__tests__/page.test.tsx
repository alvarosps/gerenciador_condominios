/**
 * Unit tests for Contract Template Editor Page.
 *
 * Tests all user interactions and component behavior:
 * - Template loading and display
 * - Monaco Editor integration
 * - Save/revert/preview functionality
 * - Change detection
 * - Backup modal and restore
 * - Tab switching
 * - Error handling
 *
 * Coverage: User interactions, state management, API integration.
 *
 * The contract-template query/mutation hooks hit MSW for real — none of them is replaced with a
 * test double. Only non-API modules (Monaco/WysiwygEditor/RulesEditor — heavy editor widgets
 * unrenderable in jsdom) are mocked.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { type ReactNode } from 'react';
import { http, HttpResponse } from 'msw';
import { server } from '@/tests/mocks/server';
import { toast } from 'sonner';
import ContractTemplatePage from '../page';

const API_BASE = 'http://localhost:8008/api';

// Mock Monaco Editor
vi.mock('@monaco-editor/react', () => ({
  default: ({
    value,
    onChange,
    ...props
  }: {
    value: string;
    onChange: (value: string | undefined) => void;
    [key: string]: unknown;
  }) => (
    <textarea
      data-testid="monaco-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      {...props}
    />
  ),
}));

// Mock WysiwygEditor — page defaults to wysiwyg mode, so this is what the tests interact with
vi.mock('@/components/contract-editor', () => ({
  WysiwygEditor: ({
    value,
    onChange,
  }: {
    value: string;
    onChange: (v: string) => void;
    className?: string;
  }) => (
    <textarea
      data-testid="monaco-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));

// Mock RulesEditor — rendered in the "rules" tab
vi.mock('@/components/contract-editor/rules-editor', () => ({
  RulesEditor: () => <div data-testid="rules-editor" />,
}));

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function Wrapper({ children }: { children: ReactNode }) {
  const queryClient = createTestQueryClient();
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

function setTemplateContent(content: string) {
  server.use(http.get(`${API_BASE}/templates/current/`, () => HttpResponse.json({ content })));
}

function setBackups(backups: unknown[]) {
  server.use(http.get(`${API_BASE}/templates/backups/`, () => HttpResponse.json(backups)));
}

function spySaveTemplate() {
  const calls: string[] = [];
  server.use(
    http.post(`${API_BASE}/templates/save/`, async ({ request }) => {
      const body = (await request.json()) as { content: string };
      calls.push(body.content);
      return HttpResponse.json({
        message: 'Template salvo com sucesso!',
        version_id: 2,
        label: '05/04/2026 12:00:00',
      });
    })
  );
  return calls;
}

function setSaveError(errorMessage: string) {
  server.use(
    http.post(`${API_BASE}/templates/save/`, () =>
      HttpResponse.json({ error: errorMessage }, { status: 400 })
    )
  );
}

function spyPreviewTemplate() {
  const calls: { content: string }[] = [];
  server.use(
    http.post(`${API_BASE}/templates/preview/`, async ({ request }) => {
      const body = (await request.json()) as { content: string; lease_id?: number };
      calls.push({ content: body.content });
      return HttpResponse.json({ html: '<html><body>John Doe</body></html>' });
    })
  );
  return calls;
}

function spyRestoreBackup() {
  const calls: number[] = [];
  server.use(
    http.post(`${API_BASE}/templates/restore/`, async ({ request }) => {
      const body = (await request.json()) as { version_id: number };
      calls.push(body.version_id);
      return HttpResponse.json({
        message: "Template restaurado com sucesso para a versão 'Padrão'.",
        version_id: body.version_id,
        label: 'Padrão',
      });
    })
  );
  return calls;
}

describe('ContractTemplatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setBackups([]);
  });

  describe('Template Loading', () => {
    it('should display loading state initially', () => {
      server.use(
        http.get(`${API_BASE}/templates/current/`, async () => {
          await new Promise((resolve) => setTimeout(resolve, 50));
          return HttpResponse.json({ content: '<html></html>' });
        })
      );

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      expect(screen.getByText(/carregando template/i)).toBeInTheDocument();
    });

    it('should load and display template content', async () => {
      const mockContent = '<html><body>Test Template</body></html>';
      setTemplateContent(mockContent);

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await waitFor(() => {
        const editor = screen.getByTestId('monaco-editor');
        expect(editor).toHaveValue(mockContent);
      });
    });
  });

  describe('Change Detection', () => {
    it('should show "Alterações não salvas" tag when content changes', async () => {
      const user = userEvent.setup();
      const mockContent = '<html><body>Original</body></html>';
      setTemplateContent(mockContent);

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      const editor = await screen.findByTestId('monaco-editor');

      // Initially no changes tag
      expect(screen.queryByText(/alterações não salvas/i)).not.toBeInTheDocument();

      // Modify content
      await user.clear(editor);
      await user.type(editor, '<html><body>Modified</body></html>');

      // Should show changes tag
      await waitFor(() => {
        expect(screen.getByText(/alterações não salvas/i)).toBeInTheDocument();
      });
    });

    it('should disable save button when no changes', async () => {
      const mockContent = '<html><body>Content</body></html>';
      setTemplateContent(mockContent);

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /salvar/i });
        expect(saveButton).toBeDisabled();
      });
    });

    it('should enable save button when content changes', async () => {
      const user = userEvent.setup();
      const mockContent = '<html><body>Original</body></html>';
      setTemplateContent(mockContent);

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      const editor = await screen.findByTestId('monaco-editor');

      // Modify content
      await user.clear(editor);
      await user.type(editor, '<html>New</html>');

      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /salvar/i });
        expect(saveButton).not.toBeDisabled();
      });
    });
  });

  describe('Save Functionality', () => {
    it('should save template successfully', async () => {
      const user = userEvent.setup();
      const mockContent = '<html><body>Original</body></html>';
      setTemplateContent(mockContent);
      const calls = spySaveTemplate();

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      const editor = await screen.findByTestId('monaco-editor');

      // Modify content
      await user.clear(editor);
      const newContent = '<html>New Content</html>';
      await user.type(editor, newContent);

      // Click save
      const saveButton = screen.getByRole('button', { name: /salvar/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(calls).toEqual([newContent]);
        expect(toast.success).toHaveBeenCalledWith('Template salvo com sucesso!');
      });
    });

    it('should not save empty template', async () => {
      const user = userEvent.setup();
      const mockContent = '<html><body>Original</body></html>';
      setTemplateContent(mockContent);
      const calls = spySaveTemplate();

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      const editor = await screen.findByTestId('monaco-editor');

      // Clear content
      await user.clear(editor);

      // Try to save
      const saveButton = screen.getByRole('button', { name: /salvar/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(calls).toHaveLength(0);
        expect(toast.error).toHaveBeenCalledWith('O template não pode estar vazio');
      });
    });

    it('should handle save error', async () => {
      const user = userEvent.setup();
      const mockContent = '<html>Original</html>';
      setTemplateContent(mockContent);
      setSaveError('Failed to save template');

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      const editor = await screen.findByTestId('monaco-editor');

      // Modify content
      await user.clear(editor);
      await user.type(editor, '<html>New</html>');

      // Click save
      const saveButton = screen.getByRole('button', { name: /salvar/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to save template');
      });
    });
  });

  describe('Preview Functionality', () => {
    it('should generate preview successfully', async () => {
      const user = userEvent.setup();
      const mockContent = '<html><body>{{ tenant.name }}</body></html>';
      setTemplateContent(mockContent);
      const calls = spyPreviewTemplate();

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await screen.findByTestId('monaco-editor');

      // Click preview button
      const previewButton = screen.getByRole('button', { name: /preview/i });
      await user.click(previewButton);

      await waitFor(() => {
        expect(calls).toEqual([{ content: mockContent }]);
        expect(toast.success).toHaveBeenCalledWith('Preview gerado com sucesso!');
      });
    });

    it('should switch to preview tab after generating preview', async () => {
      const user = userEvent.setup();
      const mockContent = '<html>Test</html>';
      setTemplateContent(mockContent);
      spyPreviewTemplate();

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await screen.findByTestId('monaco-editor');

      // Click preview
      const previewButton = screen.getByRole('button', { name: /preview/i });
      await user.click(previewButton);

      await waitFor(() => {
        // Preview tab should be active (contains iframe with rendered HTML)
        const iframe = screen.getByTitle('Preview');
        expect(iframe).toBeInTheDocument();
      });
    });

    it('should not preview empty template', async () => {
      const user = userEvent.setup();
      const mockContent = '<html>Original</html>';
      setTemplateContent(mockContent);
      const calls = spyPreviewTemplate();

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      const editor = await screen.findByTestId('monaco-editor');

      // Clear content
      await user.clear(editor);

      // Try to preview
      const previewButton = screen.getByRole('button', { name: /preview/i });
      await user.click(previewButton);

      await waitFor(() => {
        expect(calls).toHaveLength(0);
        expect(toast.error).toHaveBeenCalledWith('O template não pode estar vazio');
      });
    });
  });

  describe('Revert Functionality', () => {
    it('should revert changes to original content', async () => {
      const user = userEvent.setup();
      const mockContent = '<html><body>Original</body></html>';
      setTemplateContent(mockContent);

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      const editor = await screen.findByTestId('monaco-editor');

      // Modify content
      await user.clear(editor);
      await user.type(editor, '<html>Modified</html>');

      // Click revert
      const revertButton = screen.getByRole('button', { name: /reverter/i });
      await user.click(revertButton);

      await waitFor(() => {
        expect(editor).toHaveValue(mockContent);
        expect(toast.info).toHaveBeenCalledWith('Alterações revertidas');
      });
    });

    it('should disable revert button when no changes', async () => {
      const mockContent = '<html>Content</html>';
      setTemplateContent(mockContent);

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await waitFor(() => {
        const revertButton = screen.getByRole('button', { name: /reverter/i });
        expect(revertButton).toBeDisabled();
      });
    });
  });

  describe('Backup Modal', () => {
    it('should render backups button', async () => {
      setTemplateContent('<html>Test</html>');

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      // Verify backup button exists
      const backupsButton = await screen.findByRole('button', { name: /backups/i });
      expect(backupsButton).toBeInTheDocument();
    });

    it('should list template versions by id in the backups modal', async () => {
      const user = userEvent.setup();
      setTemplateContent('<html>Test</html>');
      setBackups([
        {
          id: 1,
          label: 'Padrão',
          created_at: '2026-04-05T12:00:00',
          is_default: true,
          is_active: false,
        },
        {
          id: 2,
          label: '05/04/2026 12:00:00',
          created_at: '2026-04-05T12:00:00',
          is_default: false,
          is_active: true,
        },
      ]);

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await user.click(await screen.findByRole('button', { name: /backups/i }));

      expect(screen.getByText('Padrão')).toBeInTheDocument();
      expect(screen.getByText('05/04/2026 12:00:00')).toBeInTheDocument();
      // The active version is marked and not restorable.
      expect(screen.getByText(/em uso/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^ativo$/i })).toBeDisabled();
    });

    it('should restore a version by id', async () => {
      const user = userEvent.setup();
      setTemplateContent('<html>Test</html>');
      setBackups([
        {
          id: 1,
          label: 'Padrão',
          created_at: '2026-04-05T12:00:00',
          is_default: true,
          is_active: false,
        },
      ]);
      const calls = spyRestoreBackup();

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await user.click(await screen.findByRole('button', { name: /backups/i }));
      await user.click(screen.getByRole('button', { name: /restaurar/i }));

      // Confirm in the alert dialog.
      await user.click(screen.getByRole('button', { name: /sim, restaurar/i }));

      await waitFor(() => {
        // The restore is invoked with the integer version id, never a filename.
        expect(calls).toEqual([1]);
        expect(toast.success).toHaveBeenCalledWith(
          "Template restaurado com sucesso para a versão 'Padrão'."
        );
      });
    });
  });

  describe('Tab Navigation', () => {
    it('should display editor on mount', async () => {
      setTemplateContent('<html>Test</html>');

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      // Verify Monaco editor is rendered (tabs are working if editor shows)
      await waitFor(() => {
        const editor = screen.getByTestId('monaco-editor');
        expect(editor).toBeInTheDocument();
      });
    });
  });
});
