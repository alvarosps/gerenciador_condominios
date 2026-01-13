/**
 * Centralized error handling utilities.
 *
 * Provides consistent error message extraction and logging
 * across the application.
 */

import { AxiosError } from 'axios';

/**
 * Type guard to check if an error is an AxiosError.
 */
export function isAxiosError(error: unknown): error is AxiosError {
  return (
    error instanceof Error &&
    'isAxiosError' in error &&
    (error as AxiosError).isAxiosError === true
  );
}

/**
 * Type guard to check if an error is a network error (no response from server).
 */
export function isNetworkError(error: unknown): boolean {
  return isAxiosError(error) && !error.response;
}

/**
 * Type guard to check if an error is an authentication error (401).
 */
export function isAuthError(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 401;
}

/**
 * Type guard to check if an error is a validation error (400).
 */
export function isValidationError(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 400;
}

/**
 * Type guard to check if an error is a forbidden error (403).
 */
export function isForbiddenError(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 403;
}

/**
 * Type guard to check if an error is a not found error (404).
 */
export function isNotFoundError(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 404;
}

/**
 * Type guard to check if an error is a server error (5xx).
 */
export function isServerError(error: unknown): boolean {
  return (
    isAxiosError(error) &&
    error.response?.status !== undefined &&
    error.response.status >= 500
  );
}

/**
 * Extract a user-friendly error message from various error types.
 *
 * @param error - The error to extract a message from
 * @param defaultMessage - Default message if extraction fails
 * @returns A user-friendly error message
 *
 * @example
 * ```ts
 * try {
 *   await api.createTenant(data);
 * } catch (error) {
 *   toast.error(getErrorMessage(error, 'Erro ao criar inquilino'));
 * }
 * ```
 */
export function getErrorMessage(
  error: unknown,
  defaultMessage = 'Ocorreu um erro inesperado'
): string {
  // Handle AxiosError with response data
  if (isAxiosError(error)) {
    const responseData = error.response?.data as Record<string, unknown> | undefined;

    // Check for common error response formats
    if (responseData) {
      // Format: { error: "message" }
      if (typeof responseData.error === 'string') {
        return responseData.error;
      }
      // Format: { message: "message" }
      if (typeof responseData.message === 'string') {
        return responseData.message;
      }
      // Format: { detail: "message" } (DRF style)
      if (typeof responseData.detail === 'string') {
        return responseData.detail;
      }
      // Format: { non_field_errors: ["message"] } (DRF validation)
      if (Array.isArray(responseData.non_field_errors)) {
        return responseData.non_field_errors.join(', ');
      }
    }

    // Network error
    if (isNetworkError(error)) {
      return 'Erro de conexão. Verifique sua internet.';
    }

    // HTTP status based messages
    const status = error.response?.status;
    switch (status) {
      case 400:
        return 'Dados inválidos. Verifique os campos.';
      case 401:
        return 'Sessão expirada. Faça login novamente.';
      case 403:
        return 'Você não tem permissão para esta ação.';
      case 404:
        return 'Recurso não encontrado.';
      case 500:
        return 'Erro no servidor. Tente novamente mais tarde.';
    }
  }

  // Standard Error object
  if (error instanceof Error) {
    return error.message;
  }

  // String error
  if (typeof error === 'string') {
    return error;
  }

  return defaultMessage;
}

/**
 * Log an error with context for debugging.
 *
 * @param error - The error to log
 * @param context - Description of where the error occurred
 *
 * @example
 * ```ts
 * try {
 *   await api.createTenant(data);
 * } catch (error) {
 *   handleError(error, 'TenantForm.handleSubmit');
 *   toast.error(getErrorMessage(error));
 * }
 * ```
 */
export function handleError(error: unknown, context: string): void {
  const message = getErrorMessage(error);
  console.error(`[${context}] ${message}`, error);

  // Here you could also send to an error tracking service like Sentry:
  // Sentry.captureException(error, { extra: { context } });
}
