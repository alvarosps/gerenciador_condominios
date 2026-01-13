import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';

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
    queryKey: ['contract-template'],
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
      queryClient.invalidateQueries({ queryKey: ['contract-template'] });
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
    queryKey: ['template-backups'],
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
      queryClient.invalidateQueries({ queryKey: ['contract-template'] });
      queryClient.invalidateQueries({ queryKey: ['template-backups'] });
    },
  });
}
