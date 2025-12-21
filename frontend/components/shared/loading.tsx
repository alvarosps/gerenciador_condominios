import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingProps {
  tip?: string;
  fullScreen?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function Loading({
  tip = 'Carregando...',
  fullScreen = false,
  size = 'md'
}: LoadingProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  const content = (
    <div className="flex flex-col items-center justify-center gap-2">
      <Loader2 className={cn('animate-spin text-primary', sizeClasses[size])} />
      {tip && (
        <p className="text-sm text-muted-foreground">{tip}</p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        {content}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center p-8">
      {content}
    </div>
  );
}
