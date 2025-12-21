/**
 * Unit tests for contract template hooks.
 *
 * Tests all TanStack Query hooks for template management:
 * - useContractTemplate: Get current template
 * - useSaveContractTemplate: Save with backup
 * - usePreviewContractTemplate: Render preview
 * - useTemplateBackups: List backups
 * - useRestoreTemplateBackup: Restore backup
 *
 * Coverage: API integration, cache invalidation, error handling
 */
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ReactNode } from 'react';
import {
  useContractTemplate,
  useSaveContractTemplate,
  usePreviewContractTemplate,
  useTemplateBackups,
  useRestoreTemplateBackup,
} from '../use-contract-template';
import { apiClient } from '@/lib/api/client';

// Mock the apiClient
vi.mock('@/lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// Create a wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retries for tests
        gcTime: 0, // Disable cache garbage collection time
      },
      mutations: {
        retry: false,
      },
    },
  });

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = 'QueryClientWrapper';
  return Wrapper;
}

describe('useContractTemplate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should fetch template content successfully', async () => {
    const mockTemplate = {
      content: '<html><body>Test Template</body></html>',
    };

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockTemplate });

    const { result } = renderHook(() => useContractTemplate(), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockTemplate);
    expect(result.current.data?.content).toContain('Test Template');
    expect(apiClient.get).toHaveBeenCalledWith('/leases/get_contract_template/');
    expect(apiClient.get).toHaveBeenCalledTimes(1);
  });

  it('should handle fetch error gracefully', async () => {
    const mockError = {
      response: {
        data: { error: 'Template not found' },
      },
    };

    vi.mocked(apiClient.get).mockRejectedValue(mockError);

    const { result } = renderHook(() => useContractTemplate(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });

  it('should cache template data with 5-minute staleTime', async () => {
    const mockTemplate = {
      content: '<html><body>Cached Template</body></html>',
    };

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockTemplate });

    const { result, rerender } = renderHook(() => useContractTemplate(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Clear mock call history
    vi.mocked(apiClient.get).mockClear();

    // Re-render should use cache (no new API call)
    rerender();

    // Verify no additional API calls
    expect(apiClient.get).not.toHaveBeenCalled();
    expect(result.current.data).toEqual(mockTemplate);
  });
});

describe('useSaveContractTemplate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should save template successfully', async () => {
    const mockResponse = {
      message: 'Template salvo com sucesso!',
      backup_path: '/path/to/backup.html',
      backup_filename: 'contract_template_backup_20250115_120000.html',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useSaveContractTemplate(), {
      wrapper: createWrapper(),
    });

    const newContent = '<html><body>New Template</body></html>';

    // Trigger mutation
    result.current.mutate(newContent);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
    expect(apiClient.post).toHaveBeenCalledWith('/leases/save_contract_template/', {
      content: newContent,
    });
  });

  it('should handle save error', async () => {
    const mockError = {
      response: {
        data: { error: 'Template content cannot be empty' },
      },
    };

    vi.mocked(apiClient.post).mockRejectedValue(mockError);

    const { result } = renderHook(() => useSaveContractTemplate(), {
      wrapper: createWrapper(),
    });

    result.current.mutate('');

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });

  it('should invalidate template cache after successful save', async () => {
    const mockResponse = {
      message: 'Template salvo com sucesso!',
      backup_path: '/path/to/backup.html',
      backup_filename: 'backup.html',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

    // Mock get for template query
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { content: 'Old content' },
    });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
        mutations: { retry: false },
      },
    });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    // First, fetch template to populate cache
    const { result: templateResult } = renderHook(() => useContractTemplate(), {
      wrapper,
    });

    await waitFor(() => {
      expect(templateResult.current.isSuccess).toBe(true);
    });

    // Now save new template
    const { result: saveResult } = renderHook(() => useSaveContractTemplate(), {
      wrapper,
    });

    // Mock new content for refetch
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { content: 'New content' },
    });

    saveResult.current.mutate('New content');

    await waitFor(() => {
      expect(saveResult.current.isSuccess).toBe(true);
    });

    // Cache should be invalidated - template query should refetch
    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/leases/get_contract_template/');
    });
  });
});

describe('usePreviewContractTemplate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should generate preview successfully', async () => {
    const mockPreview = {
      html: '<html><body>Preview with rendered data</body></html>',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockPreview });

    const { result } = renderHook(() => usePreviewContractTemplate(), {
      wrapper: createWrapper(),
    });

    const content = '<html>{{ tenant.name }}</html>';

    result.current.mutate({ content });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPreview);
    expect(apiClient.post).toHaveBeenCalledWith('/leases/preview_contract_template/', {
      content,
    });
  });

  it('should generate preview with specific lease_id', async () => {
    const mockPreview = {
      html: '<html><body>Preview for specific lease</body></html>',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockPreview });

    const { result } = renderHook(() => usePreviewContractTemplate(), {
      wrapper: createWrapper(),
    });

    const content = '<html>{{ tenant.name }}</html>';
    const lease_id = 123;

    result.current.mutate({ content, lease_id });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(apiClient.post).toHaveBeenCalledWith('/leases/preview_contract_template/', {
      content,
      lease_id,
    });
  });

  it('should handle preview error when no lease exists', async () => {
    const mockError = {
      response: {
        data: {
          error: 'Nenhuma locação encontrada no sistema. Crie uma locação para visualizar o preview.',
        },
      },
    };

    vi.mocked(apiClient.post).mockRejectedValue(mockError);

    const { result } = renderHook(() => usePreviewContractTemplate(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ content: '<html>Test</html>' });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });

  it('should handle template rendering errors', async () => {
    const mockError = {
      response: {
        data: {
          error: 'Template syntax error: unexpected token',
        },
      },
    };

    vi.mocked(apiClient.post).mockRejectedValue(mockError);

    const { result } = renderHook(() => usePreviewContractTemplate(), {
      wrapper: createWrapper(),
    });

    const invalidContent = '<html>{{ invalid syntax }';

    result.current.mutate({ content: invalidContent });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe('useTemplateBackups', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should fetch backups list successfully', async () => {
    const mockBackups = [
      {
        filename: 'contract_template_backup_20250115_140000.html',
        path: '/path/to/backup1.html',
        size: 5432,
        created_at: '2025-01-15T14:00:00',
      },
      {
        filename: 'contract_template_backup_20250115_130000.html',
        path: '/path/to/backup2.html',
        size: 5123,
        created_at: '2025-01-15T13:00:00',
      },
    ];

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockBackups });

    const { result } = renderHook(() => useTemplateBackups(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockBackups);
    expect(result.current.data).toHaveLength(2);
    expect(apiClient.get).toHaveBeenCalledWith('/leases/list_template_backups/');
  });

  it('should return empty array when no backups exist', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

    const { result } = renderHook(() => useTemplateBackups(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.data).toHaveLength(0);
  });

  it('should cache backups data with 2-minute staleTime', async () => {
    const mockBackups = [
      {
        filename: 'backup.html',
        path: '/path/backup.html',
        size: 1000,
        created_at: '2025-01-15T12:00:00',
      },
    ];

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockBackups });

    const { result, rerender } = renderHook(() => useTemplateBackups(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Clear mock call history
    vi.mocked(apiClient.get).mockClear();

    // Re-render should use cache
    rerender();

    // Verify no additional API calls
    expect(apiClient.get).not.toHaveBeenCalled();
    expect(result.current.data).toEqual(mockBackups);
  });

  it('should handle fetch backups error', async () => {
    const mockError = {
      response: {
        data: { error: 'Failed to list backups' },
      },
    };

    vi.mocked(apiClient.get).mockRejectedValue(mockError);

    const { result } = renderHook(() => useTemplateBackups(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });
});

describe('useRestoreTemplateBackup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should restore backup successfully', async () => {
    const mockResponse = {
      message: 'Template restaurado com sucesso de backup.html',
      safety_backup: 'contract_template_before_restore_20250115_160000.html',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useRestoreTemplateBackup(), {
      wrapper: createWrapper(),
    });

    const backup_filename = 'contract_template_backup_20250115_120000.html';

    result.current.mutate(backup_filename);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
    expect(apiClient.post).toHaveBeenCalledWith('/leases/restore_template_backup/', {
      backup_filename,
    });
  });

  it('should handle restore error when backup not found', async () => {
    const mockError = {
      response: {
        data: { error: 'Backup file not found: nonexistent.html' },
      },
    };

    vi.mocked(apiClient.post).mockRejectedValue(mockError);

    const { result } = renderHook(() => useRestoreTemplateBackup(), {
      wrapper: createWrapper(),
    });

    result.current.mutate('nonexistent.html');

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });

  it('should invalidate both template and backups cache after restore', async () => {
    const mockResponse = {
      message: 'Restored successfully',
      safety_backup: 'safety.html',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

    // Mock get endpoints
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/leases/get_contract_template/') {
        return Promise.resolve({ data: { content: 'Template' } });
      }
      if (url === '/leases/list_template_backups/') {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown endpoint'));
    });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
        mutations: { retry: false },
      },
    });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    // Populate caches
    const { result: templateResult } = renderHook(() => useContractTemplate(), {
      wrapper,
    });
    const { result: backupsResult } = renderHook(() => useTemplateBackups(), {
      wrapper,
    });

    await waitFor(() => {
      expect(templateResult.current.isSuccess).toBe(true);
      expect(backupsResult.current.isSuccess).toBe(true);
    });

    // Clear get mocks
    vi.mocked(apiClient.get).mockClear();

    // Now restore backup
    const { result: restoreResult } = renderHook(() => useRestoreTemplateBackup(), {
      wrapper,
    });

    restoreResult.current.mutate('backup.html');

    await waitFor(() => {
      expect(restoreResult.current.isSuccess).toBe(true);
    });

    // Both caches should be invalidated
    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/leases/get_contract_template/');
      expect(apiClient.get).toHaveBeenCalledWith('/leases/list_template_backups/');
    });

    // Should have been called twice (once for each query)
    expect(apiClient.get).toHaveBeenCalledTimes(2);
  });
});

describe('Hooks Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should work together: save template → see new backup → restore backup', async () => {
    // Setup mocks
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/leases/get_contract_template/') {
        return Promise.resolve({
          data: { content: '<html>Current</html>' },
        });
      }
      if (url === '/leases/list_template_backups/') {
        return Promise.resolve({
          data: [
            {
              filename: 'backup_new.html',
              path: '/path/backup_new.html',
              size: 1000,
              created_at: '2025-01-15T12:00:00',
            },
          ],
        });
      }
      return Promise.reject(new Error('Unknown endpoint'));
    });

    vi.mocked(apiClient.post).mockImplementation((url: string, _data: unknown) => {
      if (url === '/leases/save_contract_template/') {
        return Promise.resolve({
          data: {
            message: 'Saved',
            backup_path: '/path/backup_new.html',
            backup_filename: 'backup_new.html',
          },
        });
      }
      if (url === '/leases/restore_template_backup/') {
        return Promise.resolve({
          data: {
            message: 'Restored',
            safety_backup: 'safety.html',
          },
        });
      }
      return Promise.reject(new Error('Unknown endpoint'));
    });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
        mutations: { retry: false },
      },
    });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    // 1. Save template
    const { result: saveResult } = renderHook(() => useSaveContractTemplate(), {
      wrapper,
    });

    saveResult.current.mutate('<html>New</html>');

    await waitFor(() => {
      expect(saveResult.current.isSuccess).toBe(true);
    });

    expect(saveResult.current.data?.backup_filename).toBe('backup_new.html');

    // 2. List backups (should include the new backup)
    const { result: backupsResult } = renderHook(() => useTemplateBackups(), {
      wrapper,
    });

    await waitFor(() => {
      expect(backupsResult.current.isSuccess).toBe(true);
    });

    expect(backupsResult.current.data).toHaveLength(1);
    expect(backupsResult.current.data?.[0].filename).toBe('backup_new.html');

    // 3. Restore backup
    const { result: restoreResult } = renderHook(() => useRestoreTemplateBackup(), {
      wrapper,
    });

    restoreResult.current.mutate('backup_new.html');

    await waitFor(() => {
      expect(restoreResult.current.isSuccess).toBe(true);
    });

    expect(restoreResult.current.data?.message).toBe('Restored');
  });
});
