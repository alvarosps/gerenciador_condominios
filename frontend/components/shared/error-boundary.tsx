'use client';

import { Component, ReactNode } from 'react';
import { Alert, Button } from 'antd';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error to console or error tracking service
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center p-4">
          <div className="w-full max-w-2xl">
            <Alert
              message="Erro inesperado"
              description={
                <div>
                  <p className="mb-4">
                    Desculpe, algo deu errado. Por favor, tente recarregar a página.
                  </p>
                  {this.state.error && (
                    <pre className="mb-4 overflow-auto rounded bg-gray-100 p-2 text-sm">
                      {this.state.error.message}
                    </pre>
                  )}
                  <Button type="primary" onClick={this.handleReset}>
                    Tentar Novamente
                  </Button>
                </div>
              }
              type="error"
              showIcon
            />
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
