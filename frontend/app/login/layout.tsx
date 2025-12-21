// Force dynamic rendering to prevent static generation issues with Ant Design
export const dynamic = 'force-dynamic';

export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
