import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { ErrorBoundary } from '../error-boundary';

/**
 * Component that throws an error when 'shouldThrow' prop is true
 */
function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }): React.ReactNode {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>Normal content</div>;
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // Suppress console.error output from React error boundary logging
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders children when no error occurs', () => {
    renderWithProviders(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Normal content')).toBeInTheDocument();
  });

  it('renders error UI when a child throws', () => {
    renderWithProviders(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Erro inesperado')).toBeInTheDocument();
    expect(screen.getByText(/desculpe, algo deu errado/i)).toBeInTheDocument();
  });

  it('renders a "Tentar Novamente" button in error state', () => {
    renderWithProviders(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(screen.getByRole('button', { name: /tentar novamente/i })).toBeInTheDocument();
  });

  it('recovers to normal rendering after reset button is clicked', () => {
    const { rerender } = renderWithProviders(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    );

    // Verify error state
    expect(screen.getByText('Erro inesperado')).toBeInTheDocument();

    // Click "Tentar Novamente" to reset the error boundary
    screen.getByRole('button', { name: /tentar novamente/i }).click();

    // Re-render with non-throwing child after reset
    rerender(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Normal content')).toBeInTheDocument();
    expect(screen.queryByText('Erro inesperado')).not.toBeInTheDocument();
  });

  it('does not show error message when children render successfully', () => {
    renderWithProviders(
      <ErrorBoundary>
        <div>Safe content</div>
      </ErrorBoundary>,
    );
    expect(screen.queryByText('Erro inesperado')).not.toBeInTheDocument();
    expect(screen.getByText('Safe content')).toBeInTheDocument();
  });
});
