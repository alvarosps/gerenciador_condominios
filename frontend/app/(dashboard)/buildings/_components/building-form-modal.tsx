'use client';

import { useEffect } from 'react';
import { Modal, Form, Input, InputNumber, message } from 'antd';
import {
  useCreateBuilding,
  useUpdateBuilding,
} from '@/lib/api/hooks/use-buildings';
import { Building, buildingSchema } from '@/lib/schemas/building.schema';

interface BuildingFormModalProps {
  open: boolean;
  building?: Building | null;
  onClose: () => void;
}

export function BuildingFormModal({
  open,
  building,
  onClose,
}: BuildingFormModalProps) {
  const [form] = Form.useForm();
  const createMutation = useCreateBuilding();
  const updateMutation = useUpdateBuilding();

  const isEditing = !!building?.id;
  const isLoading = createMutation.isPending || updateMutation.isPending;

  useEffect(() => {
    if (open) {
      if (building) {
        // Populate form with building data for editing
        form.setFieldsValue(building);
      } else {
        // Reset form for new building
        form.resetFields();
      }
    }
  }, [building, form, open]);

  const handleSubmit = async () => {
    try {
      // Validate form fields
      const values = await form.validateFields();

      // Validate with Zod schema
      const validated = buildingSchema.parse(values);

      if (isEditing && building?.id) {
        // Update existing building
        await updateMutation.mutateAsync({ ...validated, id: building.id });
        message.success('Prédio atualizado com sucesso');
      } else {
        // Create new building
        await createMutation.mutateAsync(validated);
        message.success('Prédio criado com sucesso');
      }

      // Close modal and reset form
      onClose();
      form.resetFields();
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message || 'Erro ao salvar prédio');
      } else {
        message.error('Erro ao salvar prédio');
      }
      console.error('Form validation error:', error);
    }
  };

  const handleCancel = () => {
    onClose();
    form.resetFields();
  };

  return (
    <Modal
      title={isEditing ? 'Editar Prédio' : 'Novo Prédio'}
      open={open}
      onOk={handleSubmit}
      onCancel={handleCancel}
      confirmLoading={isLoading}
      okText={isEditing ? 'Atualizar' : 'Criar'}
      cancelText="Cancelar"
      destroyOnClose
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
        autoComplete="off"
        className="mt-4"
      >
        <Form.Item
          name="street_number"
          label="Número da Rua"
          rules={[
            { required: true, message: 'Por favor, informe o número da rua' },
            {
              type: 'number',
              min: 1,
              message: 'O número deve ser maior que zero',
            },
          ]}
          tooltip="Número identificador do prédio na rua"
        >
          <InputNumber
            min={1}
            className="w-full"
            placeholder="Ex: 836"
            disabled={isLoading}
          />
        </Form.Item>

        <Form.Item
          name="name"
          label="Nome do Prédio"
          rules={[
            { required: true, message: 'Por favor, informe o nome do prédio' },
            { min: 1, message: 'O nome deve ter pelo menos 1 caractere' },
            { max: 200, message: 'O nome deve ter no máximo 200 caracteres' },
          ]}
          tooltip="Nome ou identificação do prédio"
        >
          <Input
            placeholder="Ex: Edifício Central"
            maxLength={200}
            showCount
            disabled={isLoading}
          />
        </Form.Item>

        <Form.Item
          name="address"
          label="Endereço Completo"
          rules={[
            { required: true, message: 'Por favor, informe o endereço' },
            { min: 1, message: 'O endereço deve ter pelo menos 1 caractere' },
            { max: 500, message: 'O endereço deve ter no máximo 500 caracteres' },
          ]}
          tooltip="Endereço completo do prédio"
        >
          <Input.TextArea
            rows={3}
            placeholder="Ex: Rua das Flores, 836 - Centro - São Paulo/SP"
            maxLength={500}
            showCount
            disabled={isLoading}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
