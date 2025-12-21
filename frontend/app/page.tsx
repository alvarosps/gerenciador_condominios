// Force dynamic rendering to prevent static generation issues with Ant Design
export const dynamic = 'force-dynamic';

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold">Condomínios Manager</h1>
      <p className="mt-4 text-lg">Sistema de Gerenciamento de Locações</p>
    </div>
  );
}
