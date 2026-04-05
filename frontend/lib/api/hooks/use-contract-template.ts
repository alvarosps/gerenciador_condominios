import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '@/lib/api/query-keys';

interface TemplateResponse {
  content: string;
}

interface SaveTemplateResponse {
  message: string;
  backup_path: string;
  backup_filename: string;
}

interface PreviewResponse {
  html: string;
}

interface Backup {
  filename: string;
  path: string;
  size: number;
  created_at: string;
  is_default?: boolean;
}

interface RestoreResponse {
  message: string;
  safety_backup: string;
}

/**
 * Get current contract template
 */
export function useContractTemplate() {
  return useQuery({
    queryKey: queryKeys.contractTemplate.all,
    queryFn: async () => {
      const { data } = await apiClient.get<TemplateResponse>(
        '/templates/current/'
      );
      return data;
    },
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  });
}

/**
 * Save contract template with backup
 */
export function useSaveContractTemplate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (content: string) => {
      const { data } = await apiClient.post<SaveTemplateResponse>(
        '/templates/save/',
        { content }
      );
      return data;
    },
    onSuccess: () => {
      // Invalidate template cache to fetch new content
      void queryClient.invalidateQueries({ queryKey: queryKeys.contractTemplate.all });
    },
  });
}

/**
 * Preview contract template with sample data
 */
export function usePreviewContractTemplate() {
  return useMutation({
    mutationFn: async (params: { content: string; lease_id?: number }) => {
      const { data } = await apiClient.post<PreviewResponse>(
        '/templates/preview/',
        params
      );
      return data;
    },
  });
}

/**
 * List all template backups
 */
export function useTemplateBackups() {
  return useQuery({
    queryKey: queryKeys.templateBackups.all,
    queryFn: async () => {
      const { data } = await apiClient.get<Backup[]>(
        '/templates/backups/'
      );
      return data;
    },
    staleTime: 1000 * 60 * 2, // Cache for 2 minutes
  });
}

/**
 * Restore a template backup
 */
export function useRestoreTemplateBackup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (backup_filename: string) => {
      const { data } = await apiClient.post<RestoreResponse>(
        '/templates/restore/',
        { backup_filename }
      );
      return data;
    },
    onSuccess: () => {
      // Invalidate template cache to fetch restored content
      void queryClient.invalidateQueries({ queryKey: queryKeys.contractTemplate.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.templateBackups.all });
    },
  });
}
