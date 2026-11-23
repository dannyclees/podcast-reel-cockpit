// Test mode: every test imports this first. It swaps two things while the API files load, so a test needs no setup,
// no keys and no npm install: api/_brand.js (generated at setup) becomes stub_brand.mjs, and ffmpeg-static becomes a dummy.
import { register } from 'node:module';
const stub = new URL('./stub_brand.mjs', import.meta.url).href;
const hooks = `export async function resolve(s, c, next) {
  if (s === './_brand.js') return { url: ${JSON.stringify(stub)}, shortCircuit: true };
  if (s === 'ffmpeg-static') return { url: 'data:text/javascript,export default "ffmpeg"', shortCircuit: true };
  return next(s, c);
}`;
register('data:text/javascript,' + encodeURIComponent(hooks));
