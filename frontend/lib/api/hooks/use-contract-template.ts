import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '@/lib/api/query-keys';

interface TemplateResponse {
  content: string;
}

interface SaveTemplateResponse {
  message: string;
  version_id: number;
  label: string;
}

interface PreviewResponse {
  html: string;
}

interface TemplateVersion {
  id: number;
  label: string;
  created_at: string;
  is_default: boolean;
  is_active: boolean;
}

interface RestoreResponse {
  message: string;
  version_id: number;
  label: string;
}

/**
 * Get current contract template
 */
export function useContractTemplate() {
  return useQuery({
    queryKey: queryKeys.contractTemplate.all,
    queryFn: async () => {
      const { data } = await apiClient.get<TemplateResponse>('/templates/current/');
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
      const { data } = await apiClient.post<SaveTemplateResponse>('/templates/save/', { content });
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
      const { data } = await apiClient.post<PreviewResponse>('/templates/preview/', params);
      return data;
    },
  });
}

/**
 * List all template versions (backups)
 */
export function useTemplateBackups() {
  return useQuery({
    queryKey: queryKeys.templateBackups.all,
    queryFn: async () => {
      const { data } = await apiClient.get<TemplateVersion[]>('/templates/backups/');
      return data;
    },
    staleTime: 1000 * 60 * 2, // Cache for 2 minutes
  });
}

/**
 * Restore a template version by id
 */
export function useRestoreTemplateBackup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (version_id: number) => {
      const { data } = await apiClient.post<RestoreResponse>('/templates/restore/', { version_id });
      return data;
    },
    onSuccess: () => {
      // Invalidate template cache to fetch restored content
      void queryClient.invalidateQueries({ queryKey: queryKeys.contractTemplate.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.templateBackups.all });
    },
  });
}
