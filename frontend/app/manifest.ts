import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  // theme_color = --primary token, oklch(0.55 0.15 175) → #008c6c (app/globals.css:60)
  // background_color = --background token (light), oklch(0.985 0.002 240) → #f9fafb
  // (app/globals.css:54; OKLCH→sRGB via the same pipeline as lib/utils/chart-colors.ts/culori)
  return {
    name: 'Condomínios Manager',
    short_name: 'Condomínios',
    description: 'Sistema de gerenciamento de locações',
    start_url: '/',
    display: 'standalone',
    lang: 'pt-BR',
    background_color: '#f9fafb',
    theme_color: '#008c6c',
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      {
        src: '/icons/icon-512-maskable.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'maskable',
      },
    ],
  };
}
