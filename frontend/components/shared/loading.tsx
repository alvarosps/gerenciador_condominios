import { Spin } from 'antd';

interface LoadingProps {
  tip?: string;
  fullScreen?: boolean;
}

export function Loading({ tip = 'Carregando...', fullScreen = false }: LoadingProps) {
  if (fullScreen) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spin size="large" tip={tip} />
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center p-8">
      <Spin tip={tip} />
    </div>
  );
}
