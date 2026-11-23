// POST /api/play {id, round, key}: one file to play = the preview video with the chosen mix as its only sound.
// One media element cannot drift; a muted video beside a separate mix drifted up to 3 s at 3x.
// Made on first use (ffmpeg stream copy, a few seconds), saved next to the video, and reused after that.
import { spawn } from 'node:child_process';
import { readFile, writeFile, rm } from 'node:fs/promises';
import ffmpegPath from 'ffmpeg-static';
import { rest, sign, send, readBody, download, upload } from './_sb.js';

const enc = encodeURIComponent;
function ffmpeg(args) {
  return new Promise((ok, bad) => {
    const p = spawn(ffmpegPath, args); let err = '';
    p.stderr.on('data', d => { err += d; });
    p.on('close', c => c === 0 ? ok() : bad(new Error(`ffmpeg ${c}: ${err.slice(-300)}`)));
  });
}

async function playFile(v, key) {
  if (key === 'none' || !v.tracks?.[key]) return v.video_path;   // no music, no SFX: the video's own sound
  if (v.play?.[key]) return v.play[key];
  const out = v.video_path.replace(/video\.mp4$/, `play-${key}.mp4`);
  const tmp = `/tmp/${Date.now()}-${Math.random().toString(36).slice(2)}`;
  try {
    await writeFile(`${tmp}-v.mp4`, await download(v.video_path));
    await writeFile(`${tmp}-a.m4a`, await download(v.tracks[key]));
    await ffmpeg(['-y', '-v', 'error', '-i', `${tmp}-v.mp4`, '-i', `${tmp}-a.m4a`, '-map', '0:v:0', '-map', '1:a:0', '-c', 'copy', '-shortest', '-movflags', '+faststart', `${tmp}-o.mp4`]);
    await upload(out, await readFile(`${tmp}-o.mp4`), 'video/mp4');
  } finally {
    await Promise.all(['-v.mp4', '-a.m4a', '-o.mp4'].map(x => rm(tmp + x, { force: true })));
  }
  // Merge, so two keys made at the same time do not overwrite each other.
  const [cur] = await rest(`shorts_versions?short_id=eq.${enc(v.short_id)}&round=eq.${v.round}&select=play`);
  await rest(`shorts_versions?short_id=eq.${enc(v.short_id)}&round=eq.${v.round}`, { method: 'PATCH', body: { play: { ...(cur?.play || {}), [key]: out } } });
  return out;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return send(res, 405, { error: 'POST only' });
  try {
    const b = await readBody(req);
    const key = String(b.key || 'none');
    if (!/^(sfx_)?(none|t\d+)$/.test(key)) return send(res, 400, { error: 'bad key' });
    const [v] = await rest(`shorts_versions?short_id=eq.${enc(b.id)}&round=eq.${Number(b.round)}&select=short_id,round,video_path,tracks,play`);
    if (!v) return send(res, 404, { error: 'no such version' });
    const made = !v.play?.[key];
    const path = await playFile(v, key);
    const urls = await sign([path], 7 * 86400);
    send(res, 200, { key, path, url: urls[path], made: made && path !== v.video_path });
  } catch (e) {
    send(res, 500, { error: String(e.message || e) });
  }
}
