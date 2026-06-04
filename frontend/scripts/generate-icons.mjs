import { mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const BACKGROUND = '#fbfbfc';
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, '..');
const source = readFileSync(path.join(scriptDir, 'icon-source.svg'));

const publicIconsDir = path.join(frontendDir, 'public', 'icons');
const appDir = path.join(frontendDir, 'app');
mkdirSync(publicIconsDir, { recursive: true });

// Maskable safe-zone: render the glyph at 80% and pad to 512 with the background color,
// keeping it clear of the platform mask crop.
const MASKABLE_SIZE = 512;
const MASKABLE_GLYPH = Math.round(MASKABLE_SIZE * 0.8);
const MASKABLE_PAD = (MASKABLE_SIZE - MASKABLE_GLYPH) / 2;

const targets = [
  { file: path.join(publicIconsDir, 'icon-192.png'), size: 192 },
  { file: path.join(publicIconsDir, 'icon-512.png'), size: 512 },
  { file: path.join(appDir, 'icon.png'), size: 512 },
];

for (const { file, size } of targets) {
  await sharp(source).resize(size, size).png().toFile(file);
}

await sharp(source)
  .resize(MASKABLE_GLYPH, MASKABLE_GLYPH)
  .extend({
    top: MASKABLE_PAD,
    bottom: MASKABLE_PAD,
    left: MASKABLE_PAD,
    right: MASKABLE_PAD,
    background: BACKGROUND,
  })
  .png()
  .toFile(path.join(publicIconsDir, 'icon-512-maskable.png'));

// apple-touch icon must be opaque (iOS ignores alpha) — flatten onto the solid background.
await sharp(source)
  .resize(180, 180)
  .flatten({ background: BACKGROUND })
  .png()
  .toFile(path.join(appDir, 'apple-icon.png'));

const generated = [
  'public/icons/icon-192.png',
  'public/icons/icon-512.png',
  'public/icons/icon-512-maskable.png',
  'app/icon.png',
  'app/apple-icon.png',
];
console.log('Generated PWA icons:');
for (const file of generated) {
  console.log(`  - ${file}`);
}
