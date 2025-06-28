import {
    ApartmentOutlined,
    BuildOutlined,
    FileTextOutlined,
    HomeOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
    SettingOutlined,
    UserOutlined,
} from '@ant-design/icons';
import { Button, Layout, Menu, theme, Typography } from 'antd';
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: <Link to="/">Dashboard</Link>,
    },
    {
      key: '/buildings',
      icon: <BuildOutlined />,
      label: <Link to="/buildings">Prédios</Link>,
    },
    {
      key: '/apartments',
      icon: <ApartmentOutlined />,
      label: <Link to="/apartments">Apartamentos</Link>,
    },
    {
      key: '/tenants',
      icon: <UserOutlined />,
      label: <Link to="/tenants">Inquilinos</Link>,
    },
    {
      key: '/leases',
      icon: <FileTextOutlined />,
      label: <Link to="/leases">Contratos</Link>,
    },
    {
      key: '/furnitures',
      icon: <SettingOutlined />,
      label: <Link to="/furnitures">Móveis</Link>,
    },
  ];

  return (
    <Layout className="min-h-screen">
      <Sider trigger={null} collapsible collapsed={collapsed}>
        <div className="h-8 m-4 bg-white bg-opacity-20 rounded-md flex items-center justify-center text-white font-bold">
          {collapsed ? 'CM' : 'Cond. Manager'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          className="border-r-0"
        />
      </Sider>
      <Layout>
        <Header 
          style={{ background: colorBgContainer }}
          className="p-0 flex items-center justify-between pr-6"
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            className="text-base w-16 h-16"
          />
          <Title level={4} className="m-0 text-slate-800">
            Sistema de Gerenciamento de Condomínios
          </Title>
        </Header>
        <Content
          style={{
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
          }}
          className="m-6 p-6 min-h-[280px] overflow-auto"
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
