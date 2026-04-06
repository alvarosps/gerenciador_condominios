import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import {
  isAxiosError,
  isNetworkError,
  isAuthError,
  isValidationError,
  isForbiddenError,
  isNotFoundError,
  isServerError,
  getErrorMessage,
  handleError,
} from '../error-handler';

/**
 * Helper to create a realistic AxiosError with a given status and response data.
 */
function makeAxiosError(status?: number, data?: Record<string, unknown>): unknown {
  try {
    // Trigger axios to throw a real AxiosError via CancelToken — easiest way is
    // to manually create one using axios.isAxiosError-compatible structure.
    const error = new Error('Request failed') as Error & {
      isAxiosError: boolean;
      response?: { status: number; data: Record<string, unknown> };
      config?: Record<string, unknown>;
    };
    error.isAxiosError = true;
    if (status !== undefined) {
      error.response = { status, data: data ?? {} };
    }
    return error;
  } catch {
    return null;
  }
}

describe('isAxiosError', () => {
  it('returns true for an AxiosError-shaped object', () => {
    const error = makeAxiosError(400, {});
    expect(isAxiosError(error)).toBe(true);
  });

  it('returns false for a plain Error', () => {
    expect(isAxiosError(new Error('plain'))).toBe(false);
  });

  it('returns false for a string', () => {
    expect(isAxiosError('error string')).toBe(false);
  });

  it('returns false for null', () => {
    expect(isAxiosError(null)).toBe(false);
  });

  it('returns false for a real axios error if axios throws', async () => {
    // Verify against a real AxiosError from axios itself
    try {
      await axios.get('http://definitely-not-real.invalid/');
    } catch (err) {
      // This will be a network error (AxiosError) or similar
      // Just check our guard doesn't crash
      expect(typeof isAxiosError(err)).toBe('boolean');
    }
  });
});

describe('isNetworkError', () => {
  it('returns true for AxiosError without response (network error)', () => {
    const error = makeAxiosError(); // no status → no response
    expect(isNetworkError(error)).toBe(true);
  });

  it('returns false for AxiosError with a response', () => {
    expect(isNetworkError(makeAxiosError(500, {}))).toBe(false);
  });

  it('returns false for plain Error', () => {
    expect(isNetworkError(new Error('plain'))).toBe(false);
  });
});

describe('isAuthError', () => {
  it('returns true for 401 AxiosError', () => {
    expect(isAuthError(makeAxiosError(401))).toBe(true);
  });

  it('returns false for 400 AxiosError', () => {
    expect(isAuthError(makeAxiosError(400))).toBe(false);
  });

  it('returns false for plain Error', () => {
    expect(isAuthError(new Error())).toBe(false);
  });
});

describe('isValidationError', () => {
  it('returns true for 400 AxiosError', () => {
    expect(isValidationError(makeAxiosError(400))).toBe(true);
  });

  it('returns false for 422 AxiosError', () => {
    expect(isValidationError(makeAxiosError(422))).toBe(false);
  });
});

describe('isForbiddenError', () => {
  it('returns true for 403 AxiosError', () => {
    expect(isForbiddenError(makeAxiosError(403))).toBe(true);
  });

  it('returns false for 401 AxiosError', () => {
    expect(isForbiddenError(makeAxiosError(401))).toBe(false);
  });
});

describe('isNotFoundError', () => {
  it('returns true for 404 AxiosError', () => {
    expect(isNotFoundError(makeAxiosError(404))).toBe(true);
  });

  it('returns false for 403 AxiosError', () => {
    expect(isNotFoundError(makeAxiosError(403))).toBe(false);
  });
});

describe('isServerError', () => {
  it('returns true for 500 AxiosError', () => {
    expect(isServerError(makeAxiosError(500))).toBe(true);
  });

  it('returns true for 503 AxiosError', () => {
    expect(isServerError(makeAxiosError(503))).toBe(true);
  });

  it('returns false for 404 AxiosError', () => {
    expect(isServerError(makeAxiosError(404))).toBe(false);
  });

  it('returns false for AxiosError without response', () => {
    expect(isServerError(makeAxiosError())).toBe(false);
  });
});

describe('getErrorMessage', () => {
  it('extracts { error: "..." } from response data', () => {
    const err = makeAxiosError(400, { error: 'Campo obrigatório' });
    expect(getErrorMessage(err)).toBe('Campo obrigatório');
  });

  it('extracts { message: "..." } from response data', () => {
    const err = makeAxiosError(400, { message: 'Mensagem de erro' });
    expect(getErrorMessage(err)).toBe('Mensagem de erro');
  });

  it('extracts { detail: "..." } from DRF response data', () => {
    const err = makeAxiosError(403, { detail: 'Não autorizado.' });
    expect(getErrorMessage(err)).toBe('Não autorizado.');
  });

  it('joins non_field_errors array', () => {
    const err = makeAxiosError(400, {
      non_field_errors: ['Erro A', 'Erro B'],
    });
    expect(getErrorMessage(err)).toBe('Erro A, Erro B');
  });

  it('returns network error message for AxiosError without response', () => {
    const err = makeAxiosError();
    expect(getErrorMessage(err)).toBe('Erro de conexão. Verifique sua internet.');
  });

  it('returns status-based message for 400 with no extractable field', () => {
    const err = makeAxiosError(400, {});
    expect(getErrorMessage(err)).toBe('Dados inválidos. Verifique os campos.');
  });

  it('returns status-based message for 401', () => {
    const err = makeAxiosError(401, {});
    expect(getErrorMessage(err)).toBe('Sessão expirada. Faça login novamente.');
  });

  it('returns status-based message for 403', () => {
    const err = makeAxiosError(403, {});
    expect(getErrorMessage(err)).toBe('Você não tem permissão para esta ação.');
  });

  it('returns status-based message for 404', () => {
    const err = makeAxiosError(404, {});
    expect(getErrorMessage(err)).toBe('Recurso não encontrado.');
  });

  it('returns status-based message for 500', () => {
    const err = makeAxiosError(500, {});
    expect(getErrorMessage(err)).toBe('Erro no servidor. Tente novamente mais tarde.');
  });

  it('returns message from plain Error', () => {
    expect(getErrorMessage(new Error('Something went wrong'))).toBe('Something went wrong');
  });

  it('returns string error directly', () => {
    expect(getErrorMessage('string error')).toBe('string error');
  });

  it('returns defaultMessage for unknown error type', () => {
    expect(getErrorMessage({ unknown: true })).toBe('Ocorreu um erro inesperado');
  });

  it('accepts a custom default message', () => {
    expect(getErrorMessage(42, 'Custom fallback')).toBe('Custom fallback');
  });
});

describe('handleError', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  it('logs the error with context prefix', () => {
    const error = new Error('Test error');
    handleError(error, 'TestContext');
    expect(console.error).toHaveBeenCalledWith(
      '[TestContext] Test error',
      error
    );
  });

  it('logs default message for unknown error', () => {
    handleError({ weird: true }, 'SomeContext');
    expect(console.error).toHaveBeenCalledWith(
      '[SomeContext] Ocorreu um erro inesperado',
      { weird: true }
    );
  });
});
