import { message } from 'antd';
import { useCallback, useEffect, useState } from 'react';

interface UseApiStateOptions<T> {
  immediate?: boolean;
  onSuccess?: (data: T) => void;
  onError?: (error: any) => void;
}

export function useApiState<T>(
  apiCall: () => Promise<{ data: T }>,
  options: UseApiStateOptions<T> = {}
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { immediate = true, onSuccess, onError } = options;

  const execute = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiCall();
      setData(response.data);
      onSuccess?.(response.data);
      return response.data;
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || err?.message || 'Erro desconhecido';
      setError(errorMessage);
      onError?.(err);
      message.error(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall, onSuccess, onError]);

  const refresh = useCallback(() => {
    return execute();
  }, [execute]);

  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [immediate, execute]);

  return {
    data,
    loading,
    error,
    execute,
    refresh,
    setData,
  };
}

export function useApiMutation<T, P = any>(
  apiCall: (params: P) => Promise<{ data: T }>,
  options: UseApiStateOptions<T> = {}
) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { onSuccess, onError } = options;

  const mutate = useCallback(async (params: P) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiCall(params);
      onSuccess?.(response.data);
      message.success('Operação realizada com sucesso!');
      return response.data;
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || err?.message || 'Erro desconhecido';
      setError(errorMessage);
      onError?.(err);
      message.error(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall, onSuccess, onError]);

  return {
    mutate,
    loading,
    error,
  };
}
