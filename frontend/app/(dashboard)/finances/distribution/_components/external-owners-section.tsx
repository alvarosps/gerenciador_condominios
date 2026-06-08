'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { formatCurrency } from '@/lib/utils/formatters';
import type { ExternalOwnerEntry } from '@/lib/api/hooks/use-owner-distribution';

interface ExternalOwnersSectionProps {
  externalOwners: ExternalOwnerEntry[];
  externalTotal: string;
}

export function ExternalOwnersSection({ externalOwners, externalTotal }: ExternalOwnersSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Donos externos</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Display-only (§4.7/§6): owner repass is NOT part of the condominium result. */}
        <p className="text-sm text-muted-foreground">
          Apenas informativo — repasse aos donos externos; não entra no resultado do condomínio.
        </p>
        {externalOwners.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum dono externo neste mês.</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Dono</TableHead>
                    <TableHead className="text-right">Locações</TableHead>
                    <TableHead className="text-right">Total no mês</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {externalOwners.map((owner) => (
                    <TableRow key={owner.owner_id}>
                      <TableCell className="font-medium">{owner.owner_name}</TableCell>
                      <TableCell className="text-right">{owner.leases_count}</TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(owner.rent_total)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <p className="text-right text-sm font-semibold">
              Total dos donos externos: {formatCurrency(externalTotal)}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
