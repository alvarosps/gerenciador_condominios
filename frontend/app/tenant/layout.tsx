import type { ReactNode } from 'react';
import { TenantPortalLayout } from '@/components/layouts/tenant-layout';

export const dynamic = 'force-dynamic';

export default function TenantLayout({ children }: { children: ReactNode }) {
  return <TenantPortalLayout>{children}</TenantPortalLayout>;
}
