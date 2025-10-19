'use client';

import { useState } from 'react';
import { Button, message, Space, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { DataTable } from '@/components/tables/data-table';
import { FurnitureFormModal } from './_components/furniture-form-modal';
import {
  useFurniture,
  useDeleteFurniture,
} from '@/lib/api/hooks/use-furniture';
import { Furniture } from '@/lib/schemas/furniture.schema';

export default function FurniturePage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingFurniture, setEditingFurniture] = useState<Furniture | null>(null);

  const { data: furniture, isLoading, error } = useFurniture();
  const deleteMutation = useDeleteFurniture();

  const handleEdit = (item: Furniture) => {
    setEditingFurniture(item);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('Móvel excluído com sucesso');
    } catch (error) {
      message.error('Erro ao excluir móvel. Verifique se não há apartamentos ou inquilinos vinculados.');
      console.error('Delete error:', error);
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setEditingFurniture(null);
  };

  const columns: ColumnsType<Furniture> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      sorter: (a, b) => (a.id || 0) - (b.id || 0),
    },
    {
      title: 'Nome do Móvel',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_: unknown, record: Furniture) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            size="small"
          >
            Editar
          </Button>
          <Popconfirm
            title="Excluir móvel"
            description="Tem certeza que deseja excluir este móvel?"
            onConfirm={() => handleDelete(record.id!)}
            okText="Sim"
            cancelText="Não"
            okButtonProps={{ danger: true }}
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              size="small"
              loading={deleteMutation.isPending}
            >
              Excluir
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (error) {
    message.error('Erro ao carregar móveis');
  }

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Móveis</h1>
          <p className="text-gray-600 mt-1">
            Gerencie o catálogo de móveis disponíveis
          </p>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsModalOpen(true)}
          size="large"
        >
          Novo Móvel
        </Button>
      </div>

      <DataTable
        columns={columns}
        dataSource={furniture}
        loading={isLoading}
        rowKey="id"
      />

      <FurnitureFormModal
        open={isModalOpen}
        furniture={editingFurniture}
        onClose={handleModalClose}
      />
    </div>
  );
}
