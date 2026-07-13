import type { Metadata, Viewport } from 'next';
import { Providers } from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'Condomínios Manager',
  description: 'Sistema de gerenciamento de locações',
  appleWebApp: { capable: true, statusBarStyle: 'default', title: 'Condomínios' },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  // --primary token, oklch(0.55 0.15 175) → #008c6c (app/globals.css:60)
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#008c6c' },
    { media: '(prefers-color-scheme: dark)', color: '#008c6c' },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
