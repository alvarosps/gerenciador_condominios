'use client';

import { Menu } from 'antd';
import {
  HomeOutlined,
  BuildOutlined,
  ApartmentOutlined,
  TeamOutlined,
  FileTextOutlined,
  InboxOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { usePathname, useRouter } from 'next/navigation';
import { ROUTES } from '@/lib/utils/constants';

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const menuItems = [
    {
      key: ROUTES.DASHBOARD,
      icon: <HomeOutlined />,
      label: 'Dashboard',
    },
    {
      key: ROUTES.BUILDINGS,
      icon: <BuildOutlined />,
      label: 'Prédios',
    },
    {
      key: ROUTES.APARTMENTS,
      icon: <ApartmentOutlined />,
      label: 'Apartamentos',
    },
    {
      key: ROUTES.TENANTS,
      icon: <TeamOutlined />,
      label: 'Inquilinos',
    },
    {
      key: ROUTES.LEASES,
      icon: <FileTextOutlined />,
      label: 'Locações',
    },
    {
      key: ROUTES.FURNITURE,
      icon: <InboxOutlined />,
      label: 'Móveis',
    },
    {
      key: ROUTES.CONTRACT_TEMPLATE,
      icon: <EditOutlined />,
      label: 'Template de Contrato',
    },
  ];

  const handleMenuClick = (e: { key: string }): void => {
    router.push(e.key);
  };

  return (
    <div className="h-full bg-white">
      <div className="p-4">
        <h1 className="text-xl font-bold">Condomínios Manager</h1>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[pathname]}
        items={menuItems}
        onClick={handleMenuClick}
        style={{ borderRight: 0 }}
      />
    </div>
  );
}
