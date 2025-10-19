'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { queryClient } from '@/lib/config/query-client';

const theme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
  },
};

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={ptBR} theme={theme}>
        <App>{children}</App>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
