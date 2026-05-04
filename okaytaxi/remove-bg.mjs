import sharp from 'sharp';
import { readdir } from 'fs/promises';
import path from 'path';

const files = [
  'barimed logo.jpg',
  'al capone logo.jpg',
  'magnum pub logo.jpg',
  'stekiwino logo.webp',
  '2be club logo.png',
  'ekusoft.png',
  'grupa tobi.png',
  'tajemnicza piwnica logo.png',
];

const dir = 'zdj';
const threshold = 240; // pixels brighter than this = transparent

for (const file of files) {
  const input = path.join(dir, file);
  const outName = file.replace(/\.(jpg|jpeg|webp|png)$/i, '-nobg.png');
  const output = path.join(dir, outName);

  console.log(`Processing: ${file}...`);
  try {
    const image = sharp(input).ensureAlpha();
    const { data, info } = await image.raw().toBuffer({ resolveWithObject: true });

    // Replace near-white pixels with transparent
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i], g = data[i+1], b = data[i+2];
      if (r >= threshold && g >= threshold && b >= threshold) {
        data[i+3] = 0; // make transparent
      }
    }

    await sharp(data, { raw: { width: info.width, height: info.height, channels: 4 } })
      .png()
      .toFile(output);

    console.log(`  -> Saved: ${outName}`);
  } catch (e) {
    console.error(`  ERROR: ${e.message}`);
  }
}

console.log('Done!');
