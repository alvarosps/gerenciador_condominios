'use client';

import { Input, Badge, Avatar } from 'antd';
import { SearchOutlined, BellOutlined, UserOutlined } from '@ant-design/icons';

export function Header() {
  return (
    <div className="flex items-center justify-between border-b bg-white px-6 py-4">
      <div className="flex-1 max-w-md">
        <Input
          placeholder="Buscar..."
          prefix={<SearchOutlined />}
          size="large"
          className="w-full"
        />
      </div>
      <div className="flex items-center gap-4">
        <Badge count={0} showZero={false}>
          <BellOutlined style={{ fontSize: '20px', cursor: 'pointer' }} />
        </Badge>
        <Avatar icon={<UserOutlined />} style={{ cursor: 'pointer' }} />
      </div>
    </div>
  );
}
