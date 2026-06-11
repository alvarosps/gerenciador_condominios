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
 * Coverage: User interactions, state management, API integration
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { type ReactNode } from 'react';
import ContractTemplatePage from '../page';
import * as hooks from '@/lib/api/hooks/use-contract-template';

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

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

// Mock date-fns
vi.mock('date-fns', () => ({
  formatDate: vi.fn(() => '15/01/2025'),
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

// Helper functions to create complete mock objects
function createMockQueryResult(
  overrides: Partial<ReturnType<typeof hooks.useTemplateBackups>> = {}
): ReturnType<typeof hooks.useTemplateBackups> {
  return {
    data: undefined,
    refetch: vi.fn(),
    error: null,
    isError: false,
    isPending: false,
    isLoading: false,
    isLoadingError: false,
    isRefetchError: false,
    isSuccess: false,
    status: 'pending' as const,
    dataUpdatedAt: 0,
    errorUpdatedAt: 0,
    failureCount: 0,
    failureReason: null,
    errorUpdateCount: 0,
    isFetched: false,
    isFetchedAfterMount: false,
    isFetching: false,
    isPlaceholderData: false,
    isRefetching: false,
    isStale: false,
    fetchStatus: 'idle' as const,
    ...overrides,
  } as ReturnType<typeof hooks.useTemplateBackups>;
}

function createMockMutationResult<T = ReturnType<typeof hooks.useSaveContractTemplate>>(
  overrides: Record<string, unknown> = {}
): T {
  return {
    mutateAsync: vi.fn(),
    isPending: false,
    mutate: vi.fn(),
    data: undefined,
    error: null,
    isError: false,
    isIdle: true,
    isSuccess: false,
    status: 'idle' as const,
    variables: undefined,
    failureCount: 0,
    failureReason: null,
    submittedAt: 0,
    reset: vi.fn(),
    context: undefined,
    isPaused: false,
    ...overrides,
  } as T;
}

describe('ContractTemplatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Template Loading', () => {
    it('should display loading state initially', () => {
      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: undefined,
        isLoading: true,
        isSuccess: false,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult());

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      expect(screen.getByText(/carregando template/i)).toBeInTheDocument();
    });

    it('should load and display template content', async () => {
      const mockContent = '<html><body>Test Template</body></html>';

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

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

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

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

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /salvar/i });
        expect(saveButton).toBeDisabled();
      });
    });

    it('should enable save button when content changes', async () => {
      const user = userEvent.setup();
      const mockContent = '<html><body>Original</body></html>';

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

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
      const mockSave = vi.fn().mockResolvedValue({
        message: 'Template salvo com sucesso!',
        version_id: 2,
        label: '05/04/2026 12:00:00',
      });

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(
        createMockMutationResult({ mutateAsync: mockSave })
      );

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      const { toast } = await import('sonner');

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
        expect(mockSave).toHaveBeenCalledWith(newContent);
        expect(toast.success).toHaveBeenCalledWith('Template salvo com sucesso!');
      });
    });

    it('should not save empty template', async () => {
      const user = userEvent.setup();
      const mockContent = '<html><body>Original</body></html>';
      const mockSave = vi.fn();

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(
        createMockMutationResult({ mutateAsync: mockSave })
      );

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      const { toast } = await import('sonner');

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      const editor = await screen.findByTestId('monaco-editor');

      // Clear content
      await user.clear(editor);

      // Try to save
      const saveButton = screen.getByRole('button', { name: /salvar/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockSave).not.toHaveBeenCalled();
        expect(toast.error).toHaveBeenCalledWith('O template não pode estar vazio');
      });
    });

    it('should handle save error', async () => {
      const user = userEvent.setup();
      const mockContent = '<html>Original</html>';
      const mockError = {
        response: {
          data: { error: 'Failed to save template' },
        },
      };
      const mockSave = vi.fn().mockRejectedValue(mockError);

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(
        createMockMutationResult({ mutateAsync: mockSave })
      );

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      const { toast } = await import('sonner');

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
      const mockPreview = vi.fn().mockResolvedValue({
        html: '<html><body>John Doe</body></html>',
      });

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>({
          mutateAsync: mockPreview,
        })
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      const { toast } = await import('sonner');

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await screen.findByTestId('monaco-editor');

      // Click preview button
      const previewButton = screen.getByRole('button', { name: /preview/i });
      await user.click(previewButton);

      await waitFor(() => {
        expect(mockPreview).toHaveBeenCalledWith({ content: mockContent });
        expect(toast.success).toHaveBeenCalledWith('Preview gerado com sucesso!');
      });
    });

    it('should switch to preview tab after generating preview', async () => {
      const user = userEvent.setup();
      const mockContent = '<html>Test</html>';
      const mockPreview = vi.fn().mockResolvedValue({
        html: '<html>Rendered</html>',
      });

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>({
          mutateAsync: mockPreview,
        })
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

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
      const mockPreview = vi.fn();

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>({
          mutateAsync: mockPreview,
        })
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      const { toast } = await import('sonner');

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      const editor = await screen.findByTestId('monaco-editor');

      // Clear content
      await user.clear(editor);

      // Try to preview
      const previewButton = screen.getByRole('button', { name: /preview/i });
      await user.click(previewButton);

      await waitFor(() => {
        expect(mockPreview).not.toHaveBeenCalled();
        expect(toast.error).toHaveBeenCalledWith('O template não pode estar vazio');
      });
    });
  });

  describe('Revert Functionality', () => {
    it('should revert changes to original content', async () => {
      const user = userEvent.setup();
      const mockContent = '<html><body>Original</body></html>';

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      const { toast } = await import('sonner');

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

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: mockContent },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await waitFor(() => {
        const revertButton = screen.getByRole('button', { name: /reverter/i });
        expect(revertButton).toBeDisabled();
      });
    });
  });

  describe('Backup Modal', () => {
    it('should render backups button', () => {
      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: '<html>Test</html>' },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      // Verify backup button exists
      const backupsButton = screen.getByRole('button', { name: /backups/i });
      expect(backupsButton).toBeInTheDocument();
    });

    it('should list template versions by id in the backups modal', async () => {
      const user = userEvent.setup();

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: '<html>Test</html>' },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(
        createMockQueryResult({
          data: [
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
          ],
        })
      );

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());
      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );
      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await user.click(screen.getByRole('button', { name: /backups/i }));

      expect(screen.getByText('Padrão')).toBeInTheDocument();
      expect(screen.getByText('05/04/2026 12:00:00')).toBeInTheDocument();
      // The active version is marked and not restorable.
      expect(screen.getByText(/em uso/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^ativo$/i })).toBeDisabled();
    });

    it('should restore a version by id', async () => {
      const user = userEvent.setup();
      const mockRestore = vi.fn().mockResolvedValue({
        message: "Template restaurado com sucesso para a versão 'Padrão'.",
        version_id: 1,
        label: 'Padrão',
      });

      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: '<html>Test</html>' },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(
        createMockQueryResult({
          data: [
            {
              id: 1,
              label: 'Padrão',
              created_at: '2026-04-05T12:00:00',
              is_default: true,
              is_active: false,
            },
          ],
        })
      );

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());
      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );
      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>({
          mutateAsync: mockRestore,
        })
      );

      const { toast } = await import('sonner');

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      await user.click(screen.getByRole('button', { name: /backups/i }));
      await user.click(screen.getByRole('button', { name: /restaurar/i }));

      // Confirm in the alert dialog.
      await user.click(screen.getByRole('button', { name: /sim, restaurar/i }));

      await waitFor(() => {
        // The restore is invoked with the integer version id, never a filename.
        expect(mockRestore).toHaveBeenCalledWith(1);
        expect(toast.success).toHaveBeenCalledWith(
          "Template restaurado com sucesso para a versão 'Padrão'."
        );
      });
    });
  });

  describe('Tab Navigation', () => {
    it('should display editor on mount', async () => {
      vi.spyOn(hooks, 'useContractTemplate').mockReturnValue({
        data: { content: '<html>Test</html>' },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
      } as ReturnType<typeof hooks.useContractTemplate>);

      vi.spyOn(hooks, 'useTemplateBackups').mockReturnValue(createMockQueryResult({ data: [] }));

      vi.spyOn(hooks, 'useSaveContractTemplate').mockReturnValue(createMockMutationResult());

      vi.spyOn(hooks, 'usePreviewContractTemplate').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.usePreviewContractTemplate>>()
      );

      vi.spyOn(hooks, 'useRestoreTemplateBackup').mockReturnValue(
        createMockMutationResult<ReturnType<typeof hooks.useRestoreTemplateBackup>>()
      );

      render(<ContractTemplatePage />, { wrapper: Wrapper });

      // Verify Monaco editor is rendered (tabs are working if editor shows)
      await waitFor(() => {
        const editor = screen.getByTestId('monaco-editor');
        expect(editor).toBeInTheDocument();
      });
    });
  });
});
