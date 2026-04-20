'use client';

import { useState, useCallback } from 'react';
import type { Lease } from '@/lib/schemas/lease.schema';

type ModalType = 'contract' | 'lateFee' | 'dueDate' | 'terminate' | 'adjustRent' | 'history';

interface LeaseModalsState {
  activeModal: ModalType | null;
  actionLease: Lease | null;
  historyLeaseId: number | null;
}

interface LeaseModalsActions {
  openModal: (type: ModalType, lease: Lease) => void;
  openHistory: (leaseId: number) => void;
  closeModal: () => void;
  closeHistory: () => void;
  isOpen: (type: ModalType) => boolean;
}

export function useLeaseModals(): LeaseModalsState & LeaseModalsActions {
  const [activeModal, setActiveModal] = useState<ModalType | null>(null);
  const [actionLease, setActionLease] = useState<Lease | null>(null);
  const [historyLeaseId, setHistoryLeaseId] = useState<number | null>(null);

  const openModal = useCallback((type: ModalType, lease: Lease) => {
    setActiveModal(type);
    setActionLease(lease);
  }, []);

  const openHistory = useCallback((leaseId: number) => {
    setHistoryLeaseId(leaseId);
  }, []);

  const closeModal = useCallback(() => {
    setActiveModal(null);
    setActionLease(null);
  }, []);

  const closeHistory = useCallback(() => {
    setHistoryLeaseId(null);
  }, []);

  const isOpen = useCallback(
    (type: ModalType) => activeModal === type,
    [activeModal],
  );

  return {
    activeModal,
    actionLease,
    historyLeaseId,
    openModal,
    openHistory,
    closeModal,
    closeHistory,
    isOpen,
  };
}
