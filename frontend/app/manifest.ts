import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  // theme_color = --primary token, oklch(0.55 0.15 175) → #008c6c (app/globals.css:60)
  return {
    name: 'Condomínios Manager',
    short_name: 'Condomínios',
    description: 'Sistema de gerenciamento de locações',
    start_url: '/',
    display: 'standalone',
    lang: 'pt-BR',
    background_color: '#fbfbfc',
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
