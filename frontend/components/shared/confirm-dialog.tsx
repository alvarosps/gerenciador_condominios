import { Modal } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';

const { confirm } = Modal;

interface ConfirmDialogOptions {
  title: string;
  content: string;
  onOk: () => void | Promise<void>;
  onCancel?: () => void;
  okText?: string;
  cancelText?: string;
  okType?: 'primary' | 'danger' | 'default';
}

export function showConfirmDialog({
  title,
  content,
  onOk,
  onCancel,
  okText = 'Confirmar',
  cancelText = 'Cancelar',
  okType = 'primary',
}: ConfirmDialogOptions): void {
  confirm({
    title,
    icon: <ExclamationCircleOutlined />,
    content,
    okText,
    okType,
    cancelText,
    onOk,
    onCancel,
  });
}

export function showDeleteConfirm(itemName: string, onConfirm: () => void | Promise<void>): void {
  showConfirmDialog({
    title: 'Confirmar exclusão',
    content: `Tem certeza que deseja excluir ${itemName}? Esta ação não pode ser desfeita.`,
    onOk: onConfirm,
    okText: 'Excluir',
    okType: 'danger',
  });
}
