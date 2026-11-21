import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const source = fileURLToPath(new URL('./entry.png', import.meta.url));
const targetDir = resolve(process.env.MAKEFUN_OUTPUT_DIR || '/output');
const dest = join(targetDir, 'entry.png');

mkdirSync(dirname(dest), { recursive: true });
copyFileSync(source, dest);

console.log(`copied ${source} -> ${dest}`);
