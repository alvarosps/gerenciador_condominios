/**
 * Django REST Framework paginated response type
 */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Type guard to check if response is paginated
 */
export function isPaginatedResponse<T>(
  data: PaginatedResponse<T> | T[]
): data is PaginatedResponse<T> {
  return (
    data !== null &&
    typeof data === 'object' &&
    !Array.isArray(data) &&
    'results' in data &&
    Array.isArray(data.results)
  );
}

/**
 * Extract array from potentially paginated response
 */
export function extractResults<T>(data: PaginatedResponse<T> | T[]): T[] {
  return isPaginatedResponse(data) ? data.results : data;
}
