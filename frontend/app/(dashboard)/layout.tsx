import { MainLayout } from '@/components/layouts/main-layout';

// Force dynamic rendering to prevent static generation issues with Ant Design
export const dynamic = 'force-dynamic';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <MainLayout>{children}</MainLayout>;
}
