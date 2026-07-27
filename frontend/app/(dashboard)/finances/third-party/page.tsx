'use client';

import { useEffect, useMemo, useState } from 'react';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/components/tables/data-table';
import { PageHeader } from '@/components/layouts/page-header';
import { useThirdPartyPeople } from '@/lib/api/hooks/use-third-party';
import { useAuthStore } from '@/store/auth-store';
import type { ThirdPartyPerson } from '@/lib/schemas/finances/third-party.schema';
import { buildThirdPartyColumns } from './_components/third-party-columns';
import { SettlementFormModal } from './_components/settlement-form-modal';

export default function ThirdPartyPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const [settlementOpen, setSettlementOpen] = useState(false);

  const { data: people, isLoading, error } = useThirdPartyPeople();

  useEffect(() => {
    if (error) toast.error('Erro ao carregar dívidas com terceiros');
  }, [error]);

  const columns = useMemo(() => buildThirdPartyColumns(), []);

  return (
    <div>
      <PageHeader
        title="Terceiros"
        description="Quanto os donos devem a cada pessoa que paga contas ou compra por eles"
        actions={
          isAdmin && (
            <Button onClick={() => setSettlementOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Registrar acerto
            </Button>
          )
        }
      />

      {!isLoading && (people?.length ?? 0) === 0 ? (
        <p className="rounded-md border-2 border-dashed py-12 text-center text-sm text-muted-foreground">
          Nenhuma dívida com terceiros
        </p>
      ) : (
        <DataTable<ThirdPartyPerson>
          columns={columns}
          dataSource={people}
          loading={isLoading}
          rowKey="person_id"
        />
      )}

      <SettlementFormModal open={settlementOpen} onClose={() => setSettlementOpen(false)} />
    </div>
  );
}
