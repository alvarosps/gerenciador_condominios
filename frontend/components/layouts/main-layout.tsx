'use client';

import { Layout } from 'antd';
import { Sidebar } from './sidebar';
import { Header } from './header';
import { ReactNode } from 'react';

const { Sider, Content } = Layout;

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={250} theme="light" style={{ overflow: 'auto', height: '100vh', position: 'fixed', left: 0, top: 0, bottom: 0 }}>
        <Sidebar />
      </Sider>
      <Layout style={{ marginLeft: 250 }}>
        <Header />
        <Content style={{ padding: '24px', background: '#f0f2f5' }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
