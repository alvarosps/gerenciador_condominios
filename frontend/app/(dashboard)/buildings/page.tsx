'use client';

import { useState } from 'react';
import { Button, message, Space, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { DataTable } from '@/components/tables/data-table';
import { BuildingFormModal } from './_components/building-form-modal';
import {
  useBuildings,
  useDeleteBuilding,
} from '@/lib/api/hooks/use-buildings';
import { Building } from '@/lib/schemas/building.schema';

export default function BuildingsPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingBuilding, setEditingBuilding] = useState<Building | null>(null);

  const { data: buildings, isLoading, error } = useBuildings();
  const deleteMutation = useDeleteBuilding();

  const handleEdit = (building: Building) => {
    setEditingBuilding(building);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('Prédio excluído com sucesso');
    } catch (error) {
      message.error('Erro ao excluir prédio. Verifique se não há apartamentos vinculados.');
      console.error('Delete error:', error);
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setEditingBuilding(null);
  };

  const columns: ColumnsType<Building> = [
    {
      title: 'Número',
      dataIndex: 'street_number',
      key: 'street_number',
      sorter: (a, b) => a.street_number - b.street_number,
      width: 120,
    },
    {
      title: 'Nome',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'Endereço',
      dataIndex: 'address',
      key: 'address',
      ellipsis: true,
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_: unknown, record: Building) => (
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
            title="Excluir prédio"
            description="Tem certeza que deseja excluir este prédio?"
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
    message.error('Erro ao carregar prédios');
  }

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Prédios</h1>
          <p className="text-gray-600 mt-1">
            Gerencie os prédios do condomínio
          </p>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsModalOpen(true)}
          size="large"
        >
          Novo Prédio
        </Button>
      </div>

      <DataTable
        columns={columns}
        dataSource={buildings}
        loading={isLoading}
        rowKey="id"
      />

      <BuildingFormModal
        open={isModalOpen}
        building={editingBuilding}
        onClose={handleModalClose}
      />
    </div>
  );
}
