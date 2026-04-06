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
 *
 * Uses MSW to intercept HTTP requests at the network boundary.
 * No internal code is mocked.
 */
import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import {
  useContractTemplate,
  useSaveContractTemplate,
  usePreviewContractTemplate,
  useTemplateBackups,
  useRestoreTemplateBackup,
} from '../use-contract-template';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useContractTemplate', () => {
  it('should fetch template content successfully', async () => {
    const { result } = renderHook(() => useContractTemplate(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.content).toBeDefined();
    expect(typeof result.current.data?.content).toBe('string');
  });

  it('should handle fetch error gracefully', async () => {
    server.use(
      http.get(`${API_BASE}/templates/current/`, () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useContractTemplate(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.data).toBeUndefined();
  });

  it('should cache template data on re-render', async () => {
    const { result, rerender } = renderHook(() => useContractTemplate(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const firstData = result.current.data;

    rerender();

    // Data must remain the same after re-render (cache hit)
    expect(result.current.data).toEqual(firstData);
  });
});

describe('useSaveContractTemplate', () => {
  it('should save template successfully', async () => {
    const { result } = renderHook(() => useSaveContractTemplate(), {
      wrapper: createWrapper(),
    });

    result.current.mutate('<html><body>New Template</body></html>');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.message).toBeDefined();
    expect(result.current.data?.backup_filename).toBeDefined();
  });

  it('should handle save error', async () => {
    server.use(
      http.post(`${API_BASE}/templates/save/`, () => {
        return new HttpResponse(null, { status: 400 });
      }),
    );

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
    let fetchCount = 0;

    server.use(
      http.get(`${API_BASE}/templates/current/`, () => {
        fetchCount += 1;
        return HttpResponse.json({
          content: fetchCount === 1 ? '<html>Old</html>' : '<html>New</html>',
        });
      }),
    );

    const wrapper = createWrapper();

    const { result: templateResult } = renderHook(() => useContractTemplate(), { wrapper });

    await waitFor(() => {
      expect(templateResult.current.isSuccess).toBe(true);
    });

    expect(fetchCount).toBe(1);

    const { result: saveResult } = renderHook(() => useSaveContractTemplate(), { wrapper });

    saveResult.current.mutate('<html>New</html>');

    await waitFor(() => {
      expect(saveResult.current.isSuccess).toBe(true);
    });

    // Cache invalidation triggers a refetch
    await waitFor(() => {
      expect(fetchCount).toBeGreaterThan(1);
    });
  });
});

describe('usePreviewContractTemplate', () => {
  it('should generate preview successfully', async () => {
    const { result } = renderHook(() => usePreviewContractTemplate(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ content: '<html>{{ tenant.name }}</html>' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.html).toBeDefined();
  });

  it('should generate preview with specific lease_id', async () => {
    const { result } = renderHook(() => usePreviewContractTemplate(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ content: '<html>{{ tenant.name }}</html>', lease_id: 123 });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.html).toBeDefined();
  });

  it('should handle preview error when server returns 404', async () => {
    server.use(
      http.post(`${API_BASE}/templates/preview/`, () => {
        return HttpResponse.json(
          { error: 'Nenhuma locação encontrada no sistema.' },
          { status: 404 },
        );
      }),
    );

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
    server.use(
      http.post(`${API_BASE}/templates/preview/`, () => {
        return HttpResponse.json(
          { error: 'Template syntax error: unexpected token' },
          { status: 400 },
        );
      }),
    );

    const { result } = renderHook(() => usePreviewContractTemplate(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ content: '<html>{{ invalid syntax }' });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe('useTemplateBackups', () => {
  it('should fetch backups list successfully', async () => {
    const { result } = renderHook(() => useTemplateBackups(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(Array.isArray(result.current.data)).toBe(true);
    const first = result.current.data?.[0];
    expect(first?.filename).toBeDefined();
    expect(first?.size).toBeDefined();
    expect(first?.created_at).toBeDefined();
  });

  it('should return empty array when no backups exist', async () => {
    server.use(
      http.get(`${API_BASE}/templates/backups/`, () => {
        return HttpResponse.json([]);
      }),
    );

    const { result } = renderHook(() => useTemplateBackups(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([]);
  });

  it('should handle fetch backups error', async () => {
    server.use(
      http.get(`${API_BASE}/templates/backups/`, () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

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
  it('should restore backup successfully', async () => {
    const { result } = renderHook(() => useRestoreTemplateBackup(), {
      wrapper: createWrapper(),
    });

    result.current.mutate('contract_template_backup_20260405_120000.html');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.message).toBeDefined();
    expect(result.current.data?.safety_backup).toBeDefined();
  });

  it('should handle restore error when backup not found', async () => {
    server.use(
      http.post(`${API_BASE}/templates/restore/`, () => {
        return HttpResponse.json({ error: 'Backup file not found' }, { status: 404 });
      }),
    );

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
    let templateFetchCount = 0;
    let backupsFetchCount = 0;

    server.use(
      http.get(`${API_BASE}/templates/current/`, () => {
        templateFetchCount += 1;
        return HttpResponse.json({ content: '<html>Template</html>' });
      }),
      http.get(`${API_BASE}/templates/backups/`, () => {
        backupsFetchCount += 1;
        return HttpResponse.json([]);
      }),
    );

    const wrapper = createWrapper();

    const { result: templateResult } = renderHook(() => useContractTemplate(), { wrapper });
    const { result: backupsResult } = renderHook(() => useTemplateBackups(), { wrapper });

    await waitFor(() => {
      expect(templateResult.current.isSuccess).toBe(true);
      expect(backupsResult.current.isSuccess).toBe(true);
    });

    const templateCountAfterLoad = templateFetchCount;
    const backupsCountAfterLoad = backupsFetchCount;

    const { result: restoreResult } = renderHook(() => useRestoreTemplateBackup(), { wrapper });

    restoreResult.current.mutate('backup.html');

    await waitFor(() => {
      expect(restoreResult.current.isSuccess).toBe(true);
    });

    // Both caches must be invalidated and refetched
    await waitFor(() => {
      expect(templateFetchCount).toBeGreaterThan(templateCountAfterLoad);
      expect(backupsFetchCount).toBeGreaterThan(backupsCountAfterLoad);
    });
  });
});

describe('Hooks Integration', () => {
  beforeEach(() => {
    // Override handlers to simulate a fresh state with no backups initially
    server.use(
      http.get(`${API_BASE}/templates/backups/`, () => {
        return HttpResponse.json([
          {
            filename: 'backup_new.html',
            path: '/path/backup_new.html',
            size: 1000,
            created_at: '2026-04-05T12:00:00',
          },
        ]);
      }),
    );
  });

  it('should work together: save template → see new backup → restore backup', async () => {
    const wrapper = createWrapper();

    // 1. Save template
    const { result: saveResult } = renderHook(() => useSaveContractTemplate(), { wrapper });

    saveResult.current.mutate('<html>New</html>');

    await waitFor(() => {
      expect(saveResult.current.isSuccess).toBe(true);
    });

    expect(saveResult.current.data?.backup_filename).toBeDefined();

    // 2. List backups (the handler returns one backup)
    const { result: backupsResult } = renderHook(() => useTemplateBackups(), { wrapper });

    await waitFor(() => {
      expect(backupsResult.current.isSuccess).toBe(true);
    });

    expect(backupsResult.current.data?.length).toBeGreaterThan(0);
    expect(backupsResult.current.data?.[0]?.filename).toBe('backup_new.html');

    // 3. Restore backup
    const { result: restoreResult } = renderHook(() => useRestoreTemplateBackup(), { wrapper });

    restoreResult.current.mutate('backup_new.html');

    await waitFor(() => {
      expect(restoreResult.current.isSuccess).toBe(true);
    });

    expect(restoreResult.current.data?.message).toBeDefined();
  });
});
