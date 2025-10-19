'use client';

import { useEffect } from 'react';
import { Modal, Form, Input, message } from 'antd';
import {
  useCreateFurniture,
  useUpdateFurniture,
} from '@/lib/api/hooks/use-furniture';
import { Furniture, furnitureSchema } from '@/lib/schemas/furniture.schema';

interface FurnitureFormModalProps {
  open: boolean;
  furniture?: Furniture | null;
  onClose: () => void;
}

export function FurnitureFormModal({
  open,
  furniture,
  onClose,
}: FurnitureFormModalProps) {
  const [form] = Form.useForm();
  const createMutation = useCreateFurniture();
  const updateMutation = useUpdateFurniture();

  const isEditing = !!furniture?.id;
  const isLoading = createMutation.isPending || updateMutation.isPending;

  useEffect(() => {
    if (open) {
      if (furniture) {
        // Populate form with furniture data for editing
        form.setFieldsValue(furniture);
      } else {
        // Reset form for new furniture
        form.resetFields();
      }
    }
  }, [furniture, form, open]);

  const handleSubmit = async () => {
    try {
      // Validate form fields
      const values = await form.validateFields();

      // Validate with Zod schema
      const validated = furnitureSchema.parse(values);

      if (isEditing && furniture?.id) {
        // Update existing furniture
        await updateMutation.mutateAsync({ ...validated, id: furniture.id });
        message.success('Móvel atualizado com sucesso');
      } else {
        // Create new furniture
        await createMutation.mutateAsync(validated);
        message.success('Móvel criado com sucesso');
      }

      // Close modal and reset form
      onClose();
      form.resetFields();
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message || 'Erro ao salvar móvel');
      } else {
        message.error('Erro ao salvar móvel');
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
      title={isEditing ? 'Editar Móvel' : 'Novo Móvel'}
      open={open}
      onOk={handleSubmit}
      onCancel={handleCancel}
      confirmLoading={isLoading}
      okText={isEditing ? 'Atualizar' : 'Criar'}
      cancelText="Cancelar"
      destroyOnClose
      width={500}
    >
      <Form
        form={form}
        layout="vertical"
        autoComplete="off"
        className="mt-4"
      >
        <Form.Item
          name="name"
          label="Nome do Móvel"
          rules={[
            { required: true, message: 'Por favor, informe o nome do móvel' },
            { min: 1, message: 'O nome deve ter pelo menos 1 caractere' },
            { max: 200, message: 'O nome deve ter no máximo 200 caracteres' },
          ]}
          tooltip="Nome ou descrição do móvel"
        >
          <Input
            placeholder="Ex: Sofá, Cama, Mesa"
            maxLength={200}
            showCount
            disabled={isLoading}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
