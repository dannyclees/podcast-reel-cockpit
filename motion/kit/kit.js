/* Motion kit. Deterministic helpers for one HyperFrames page of 1080 x 960 (the Short's top panel).
   One paused GSAP timeline at window.__timelines['main']. No Math.random, no clocks: every pixel is a function of time.
   Colours come from brand.css. The signature move is K.drop, chosen by brand.json motion.signature (build.py writes window.BRAND_MOTION):
   "stack": a block falls, squashes on landing, springs back, then an accent layer slides out from under it.
   "pop": it scales in with a small overshoot, no layer. "slide": it slides in from the side and settles. See motion/STYLE.md. */
(function () {
  const K = {};
  const tok = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();   // real colour values: GSAP cannot tween a var()
  K.C = { ground: tok('--ground'), onGround: tok('--on-ground'), paper: tok('--paper'), onPaper: tok('--on-paper'), panel: tok('--panel'), onPanel: tok('--on-panel'),
          accent: tok('--accent'), onAccent: tok('--on-accent'), deep: tok('--accent-deep'), alarm: tok('--alarm'), mute: tok('--mute') };
  K.signature = (window.BRAND_MOTION && window.BRAND_MOTION.signature) || 'stack';
  K.energy = { low: .6, medium: 1, high: 1.4 }[window.BRAND_MOTION && window.BRAND_MOTION.energy] || 1;   // motion.energy: how hard a block lands
  const root = () => document.getElementById('root');

  K.el = function (parent, cls, css, html) {
    const e = document.createElement('div'); if (cls) e.className = cls;
    if (css) for (const k in css) e.style[k] = typeof css[k] === 'number' && !/opacity|zIndex|lineHeight|fontWeight/.test(k) ? css[k] + 'px' : css[k];
    if (html != null) e.innerHTML = html; (parent || root()).appendChild(e); return e;
  };

  // page: ground + grain + timeline. dur = seconds of this comp.
  K.init = function (dur) {
    const r = root();
    const g = K.el(r, '', null); g.id = 'ground'; K.el(g, 'tex'); K.el(g, 'glow');
    const gr = K.el(r, ''); gr.id = 'grain'; gr.style.zIndex = 50;
    K.grains = [0, 1, 2, 3].map(k => K.el(gr, 'gr', { backgroundImage: `url(img/grain_${k}.png)` }));
    const tl = gsap.timeline({ paused: true });
    window.__timelines = window.__timelines || {}; window.__timelines['main'] = tl;
    K.tl = tl; K.DUR = dur;
    tl.fromTo('#ground .tex', { scale: 1.06 }, { scale: 1, duration: dur, ease: 'none' }, 0);   // the ground always breathes a little
    for (let t = 0; t < dur; t += 1 / 15) { const f = Math.round(t * 15) % 4;   // film grain at 15 fps, 4 plates
      K.grains.forEach((p, i) => tl.set(p, { opacity: i === f ? .16 : 0 }, t)); }
    return tl;
  };
  K.finish = function () { K.tl.to({}, { duration: K.DUR }, 0); K.tl.seek(0); };

  // a scene: everything inside appears at t0 and leaves at t1 (quick lift + fade) so the next one can land
  K.scene = function (t0, t1) {
    const s = K.el(root(), 'sc'); s.style.zIndex = 10;
    if (t0 > 0.02) { K.tl.set(s, { opacity: 0 }, 0); K.tl.set(s, { opacity: 1 }, t0 - .001); }   // a scene at 0 s is simply there
    if (t1 != null) K.tl.to(s, { opacity: 0, y: -36, duration: .16, ease: 'power2.in' }, t1 - .12);
    return s;
  };

  // a block: accent layer + face. o = {x, y, w, h, r, cls: 'paper'|'dark'|'photo'|'logo', html, img, video, contain}
  K.block = function (parent, o) {
    const b = K.el(parent, 'blk ' + (o.cls || 'paper'), { left: o.x, top: o.y, width: o.w, height: o.h, borderRadius: (o.r == null ? 28 : o.r) + 'px' });
    b.lay = K.el(b, 'lay'); b.face = K.el(b, 'face', null, o.html || '');
    if (o.img) { const i = document.createElement('img'); i.src = o.img; if (o.contain) i.className = 'contain'; if (o.pos) i.style.objectPosition = o.pos; b.face.appendChild(i); b.media = i; }
    if (o.video) { const v = document.createElement('video'); v.src = o.video; v.muted = true; v.setAttribute('muted', ''); v.setAttribute('playsinline', '');
      v.setAttribute('data-start', o.vstart || 0); v.setAttribute('data-duration', o.vdur || K.DUR); v.setAttribute('data-track-index', o.track || 1);
      if (o.contain) v.style.objectFit = 'contain'; b.face.appendChild(v); b.media = v; }
    K.tl.set(b.lay, { x: 0, y: 0, opacity: 0 }, 0);
    return b;
  };

  // the signature move. t = the moment it LANDS (put this on the word), in every style. o.side = 1 from the right, -1 from the left ("slide")
  // stack: fall, squash on the floor line, spring back; then the accent layer slides out under it
  K.drop = function (b, t, o) {
    o = o || {}; const fall = o.fall || .14, from = o.from || 520, h = b.offsetHeight || parseFloat(b.style.height) || 200;
    if (K.signature === 'pop') {
      if (t - fall < 0.001) K.tl.set(b, { scale: 1, opacity: 1 }, 0);   // lands on frame 0 (R77): already there
      else K.tl.fromTo(b, { scale: .7, opacity: 0 }, { scale: 1 + .04 * K.energy, opacity: 1, duration: fall, ease: 'power3.out', immediateRender: true }, t - fall);
      K.tl.to(b, { scale: 1, duration: .3, ease: 'back.out(3)' }, t);
      return t;
    }
    if (K.signature === 'slide') {
      const side = o.side || 1, away = side * (o.from || 1200);
      if (t - fall < 0.001) K.tl.set(b, { x: 0, opacity: 1 }, 0);
      else K.tl.fromTo(b, { x: away, opacity: 1 }, { x: 0, duration: fall + .08, ease: 'power3.out', immediateRender: true }, t - fall - .08);
      K.tl.to(b, { x: -side * 12 * K.energy, duration: .06, ease: 'power2.out' }, t);
      K.tl.to(b, { x: 0, duration: .3, ease: 'back.out(3)' }, t + .06);
      return t;
    }
    if (t - fall < 0.001) K.tl.set(b, { y: 0, opacity: 1 }, 0);   // lands on frame 0 (R77): already there, it only squashes and locks
    else K.tl.fromTo(b, { y: -from, opacity: 0 }, { y: 0, opacity: 1, duration: fall, ease: 'power3.in', immediateRender: true }, t - fall);
    K.tl.to(b, { scaleY: 1 - .08 * K.energy, scaleX: 1 + .03 * K.energy, duration: .06, ease: 'power2.out', transformOrigin: `50% ${h}px` }, t);
    K.tl.to(b, { scaleY: 1, scaleX: 1, duration: .38, ease: 'back.out(3)' }, t + .06);
    if (b.lay && o.layer !== false) K.tl.fromTo(b.lay, { x: 0, y: 0, opacity: 1 }, { x: o.dx == null ? 16 : o.dx, y: o.dy == null ? 16 : o.dy, duration: .36, ease: 'power3.out', immediateRender: false }, t + .08);
    return t;   // t = the moment it LANDS (put this on the word)
  };
  // smaller things pop in on their word
  K.pop = function (n, t, from) { K.tl.fromTo(n, { opacity: 0, scale: from || .8 }, { opacity: 1, scale: 1, duration: .32, ease: 'back.out(2.2)', immediateRender: true }, t - .05); };
  K.rise = function (n, t, dy) { K.tl.fromTo(n, { opacity: 0, y: dy || 26 }, { opacity: 1, y: 0, duration: .3, ease: 'power3.out', immediateRender: true }, t - .05); };
  K.fadeIn = function (n, t, d) { K.tl.fromTo(n, { opacity: 0 }, { opacity: 1, duration: d || .2, immediateRender: true }, t); };
  K.out = function (n, t) { K.tl.to(n, { opacity: 0, scale: .9, duration: .16, ease: 'power2.in' }, t - .1); };
  K.push = function (n, t0, t1, s) { K.tl.fromTo(n, { scale: 1 }, { scale: s || 1.08, duration: Math.max(.3, t1 - t0), ease: 'none', immediateRender: false }, t0); };
  K.kick = function (n, t, a) { K.tl.to(n, { scale: 1 + (a || .05), duration: .08, ease: 'power2.out' }, t); K.tl.to(n, { scale: 1, duration: .45, ease: 'back.out(3)' }, t + .08); };
  K.shake = function (n, t, a) { a = a || 12; for (let i = 0; i < 5; i++) K.tl.to(n, { x: (i % 2 ? -1 : 1) * a * (1 - i / 5), duration: .045, ease: 'sine.inOut' }, t + i * .045); K.tl.to(n, { x: 0, duration: .08 }, t + .225); };
  K.pulse = function (parent, cx, cy, r, t, col) {
    const ring = K.el(parent, 'ring', { left: cx - r, top: cy - r, width: 2 * r, height: 2 * r, borderColor: col || K.C.accent });
    K.tl.fromTo(ring, { opacity: .95, scale: .85 }, { opacity: 0, scale: 1.5, duration: .7, ease: 'power2.out', immediateRender: false }, t); return ring;
  };

  // big words. lines = [['ONE', 'CLAIM'], ['IN', 'WORDS']]; returns {word: span}. Words land with K.say, marks with K.mark
  K.words = function (parent, o) {
    const box = K.el(parent, 'abs disp', { left: o.x || 0, top: o.y, width: o.w || 1080, fontSize: o.size || 120, textAlign: o.align || 'center', lineHeight: o.lh || 1.04 });
    const map = {};
    o.lines.forEach(line => { const ln = K.el(box, '', { display: 'block' });
      line.forEach((w, i) => { const s = document.createElement('span'); s.className = 'w'; s.innerHTML = '<i class="mk"></i>' + w;
        ln.appendChild(s); if (i < line.length - 1) ln.appendChild(document.createTextNode(' ')); map[w] = s; }); });
    box.map = map; return box;
  };
  K.say = function (s, t) { K.tl.fromTo(s, { opacity: 0, y: -90 }, { opacity: 1, y: 0, duration: .12, ease: 'power3.in', immediateRender: true }, t - .12);
    K.tl.to(s, { scaleY: .9, duration: .05, transformOrigin: '50% 100%' }, t); K.tl.to(s, { scaleY: 1, duration: .3, ease: 'back.out(3)' }, t + .05); };
  K.mark = function (s, t) {   // title.highlight in brand.json: block (the marker), colour (the word turns accent), none
    const hl = tok('--title-highlight');
    if (hl === 'none') return;
    if (hl === 'colour' || hl === 'color') { K.tl.set(s, { color: K.C.accent }, t); return; }
    K.tl.to(s.querySelector('.mk'), { scaleX: 1, duration: .22, ease: 'power3.out' }, t); K.tl.set(s, { color: K.C.onAccent }, t + .05); };

  // a news card. text may hold <m>marked words</m>; marks wipe on in order at the given times
  K.news = function (parent, o) {
    const b = K.block(parent, { x: o.x || 90, y: o.y || 150, w: o.w || 900, h: o.h || 520, r: 30, cls: 'paper news' });
    b.face.style.padding = '44px 50px';
    b.face.innerHTML = `<div class="src"><b>${o.outlet}</b><span>${o.date || ''}</span></div><div class="t" style="margin-top:26px">${o.text.replace(/<m>/g, '<span class="m">').replace(/<\/m>/g, '</span>')}</div>`;
    b.marks = [...b.face.querySelectorAll('.m')];
    if (o.logo) { const i = document.createElement('img'); i.src = o.logo; Object.assign(i.style, { position: 'absolute', left: 'auto', top: 'auto', right: '46px', bottom: '40px', width: '110px', height: '110px', objectFit: 'contain' }); b.face.appendChild(i); }
    return b;
  };
  K.markText = function (m, t) { K.tl.to(m, { backgroundSize: '100% 100%', duration: .3, ease: 'power2.out' }, t); };

  // a number that counts to its value on the word. fmt(v) -> string
  K.count = function (node, t, from, to, dur, fmt) {
    const o = { v: from }; node.textContent = fmt(from);
    K.tl.to(o, { v: to, duration: dur || .6, ease: 'expo.out', onUpdate: () => { const s = fmt(o.v); if (node.textContent !== s) node.textContent = s; } }, t);
  };
  K.fmt = { int: v => Math.round(v).toLocaleString('en-US'), money: v => '$' + Math.round(v).toLocaleString('en-US'),
            k: v => Math.round(v) + 'K', m: v => (Math.round(v * 10) / 10) + 'M', x: v => Math.round(v) + 'x' };

  // a bar grows on its word
  K.bar = function (parent, o, t, dur) {
    const b = K.el(parent, 'bar' + (o.white ? ' w' : ''), { left: o.x, top: o.y, width: o.w, height: o.h || 84 });
    if (o.color) b.style.background = o.color;
    K.tl.fromTo(b, { scaleX: 0 }, { scaleX: 1, duration: dur || .5, ease: 'expo.out', immediateRender: true }, t); return b;
  };
  K.chip = function (parent, o) { const c = K.el(parent, 'chip', { left: o.x, top: o.y }, (o.logo ? `<img src="${o.logo}">` : '') + (o.text || '')); return c; };
  K.stamp = function (parent, o, t) {
    const s = K.el(parent, 'stamp', { left: o.x, top: o.y, fontSize: o.size || 64 }, o.text);
    K.tl.fromTo(s, { opacity: 0, scale: 1.8, rotation: o.rot || -8 }, { opacity: 1, scale: 1, rotation: o.rot || -8, duration: .18, ease: 'power4.in', immediateRender: true }, t - .18);
    return s;
  };
  K.svg = function (parent, w, h) { const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); s.setAttribute('width', w); s.setAttribute('height', h);
    s.setAttribute('viewBox', `0 0 ${w} ${h}`); s.setAttribute('class', 'layer'); parent.appendChild(s); return s; };
  K.path = function (svg, d, o) { const p = document.createElementNS('http://www.w3.org/2000/svg', 'path'); p.setAttribute('d', d);
    p.setAttribute('fill', 'none'); p.setAttribute('stroke', (o && o.stroke) || K.C.onGround); p.setAttribute('stroke-width', (o && o.width) || 8);
    p.setAttribute('stroke-linecap', 'round'); p.setAttribute('stroke-linejoin', 'round'); if (o && o.dash) p.setAttribute('stroke-dasharray', o.dash); svg.appendChild(p); return p; };
  K.draw = function (p, t, d) { const L = p.getTotalLength(); p.style.strokeDasharray = L + ' ' + L; p.style.strokeDashoffset = L;
    K.tl.to(p, { strokeDashoffset: 0, duration: d || .4, ease: 'power2.out' }, t); };

  window.K = K;
})();

/* line icons (stroke = currentColor). K.icon('store', 120) -> svg markup */
(function () {
  const P = {
    store: '<path d="M8 26h48v30H8z"/><path d="M4 26l6-16h44l6 16"/><path d="M4 26q7 8 14 0q7 8 14 0q7 8 14 0q7 8 14 0"/><path d="M26 56V40h12v16"/>',
    lockopen: '<rect x="12" y="28" width="40" height="28" rx="5"/><path d="M20 28v-9a12 12 0 0 1 23-4"/><path d="M32 40v6"/>',
    lock: '<rect x="12" y="28" width="40" height="28" rx="5"/><path d="M20 28v-9a12 12 0 0 1 24 0v9"/><path d="M32 40v6"/>',
    cloud: '<path d="M18 48h30a11 11 0 0 0 0-22a15 15 0 0 0-29-3a12 12 0 0 0-1 25z"/>',
    fridge: '<rect x="14" y="4" width="36" height="56" rx="5"/><path d="M14 24h36"/><path d="M21 12v6M21 30v10"/>',
    plug: '<path d="M24 6v12M40 6v12"/><path d="M16 18h32v10a16 16 0 0 1-32 0z"/><path d="M32 44v14"/>',
    pin: '<path d="M32 58s-18-17-18-31a18 18 0 0 1 36 0c0 14-18 31-18 31z"/><circle cx="32" cy="27" r="6"/>',
    clock: '<circle cx="32" cy="32" r="24"/><path d="M32 18v15l10 6"/>',
    person: '<circle cx="32" cy="20" r="10"/><path d="M12 58a20 20 0 0 1 40 0"/>',
    check: '<path d="M14 34l12 12l24-26"/>',
    x: '<path d="M16 16l32 32M48 16L16 48"/>',
    flask: '<path d="M24 6h16M27 6v18L12 52a5 5 0 0 0 4 7h32a5 5 0 0 0 4-7L37 24V6"/><path d="M18 42h28"/>',
    bolt: '<path d="M36 4L14 36h16l-4 24l24-34H34z"/>',
    alert: '<path d="M32 6L4 56h56z"/><path d="M32 24v14M32 46v2"/>',
    car: '<path d="M8 40l6-16h36l6 16v12H8z"/><circle cx="18" cy="52" r="5"/><circle cx="46" cy="52" r="5"/><path d="M8 40h48"/>',
    chip: '<rect x="14" y="14" width="36" height="36" rx="4"/><path d="M24 4v10M40 4v10M24 50v10M40 50v10M4 24h10M4 40h10M50 24h10M50 40h10"/>',
    gamepad: '<path d="M16 22h32a12 12 0 0 1 12 12v4a8 8 0 0 1-14 5l-4-5H22l-4 5a8 8 0 0 1-14-5v-4a12 12 0 0 1 12-12z"/><path d="M18 30v8M14 34h8"/><circle cx="44" cy="32" r="2"/><circle cx="48" cy="37" r="2"/>',
    globe: '<circle cx="32" cy="32" r="24"/><path d="M8 32h48M32 8c-9 10-9 38 0 48M32 8c9 10 9 38 0 48"/>',
    up: '<path d="M32 56V10M14 28l18-18l18 18"/>',
    walk: '<circle cx="36" cy="10" r="5"/><path d="M34 18l-8 16l10 8l-2 16M26 34l-8 12M34 22l10 8l8-2"/>',
  };
  K.icon = function (n, size, col, w) {
    return `<svg width="${size}" height="${size}" viewBox="0 0 64 64" fill="none" stroke="${col || 'currentColor'}" stroke-width="${w || 4.5}" stroke-linecap="round" stroke-linejoin="round" style="display:block">${P[n]}</svg>`;
  };
  // an icon tile: a block with one icon in it
  K.itile = function (parent, o) {
    const b = K.block(parent, Object.assign({ r: 32, cls: o.dark ? 'dark' : 'paper' }, o));
    b.face.style.display = 'flex'; b.face.style.alignItems = 'center'; b.face.style.justifyContent = 'center'; b.face.style.flexDirection = 'column'; b.face.style.gap = '10px';
    b.face.innerHTML = K.icon(o.icon, o.isize || Math.round(o.w * .52), o.col || (o.dark ? K.C.onPanel : K.C.onPaper), o.sw) + (o.label ? `<div class="lab" style="font-size:${o.lsize || 34}px;color:${o.dark ? K.C.onPanel : K.C.onPaper}">${o.label}</div>` : '');
    return b;
  };
})();

/* zoom inside a photo block: show crop box b = [x0, y0, x1, y1] (image px) of an image iw x ih, fitted (contain) into the block */
(function () {
  K.fitBox = function (bw, bh, iw, ih, b) {
    const s = Math.min(bw / (b[2] - b[0]), bh / (b[3] - b[1]));
    return { width: iw * s, height: ih * s, left: -b[0] * s + (bw - (b[2] - b[0]) * s) / 2, top: -b[1] * s + (bh - (b[3] - b[1]) * s) / 2 };
  };
  // a photo block whose image can be steered to crop boxes on words. o = {x, y, w, h, img, iw, ih, box}
  K.zphoto = function (parent, o) {
    const b = K.block(parent, Object.assign({ cls: 'photo' }, o, { img: null }));
    const i = document.createElement('img'); i.src = o.img; Object.assign(i.style, { position: 'absolute', objectFit: 'fill', inset: 'auto', maxWidth: 'none' });
    b.face.appendChild(i); b.zimg = i; b.zo = o; b.face.style.background = o.bg || K.C.paper;
    const f = K.fitBox(o.w, o.h, o.iw, o.ih, o.box || [0, 0, o.iw, o.ih]);
    for (const k in f) i.style[k] = f[k] + 'px';
    return b;
  };
  K.zoomTo = function (b, t, box, d) {
    const f = K.fitBox(b.zo.w, b.zo.h, b.zo.iw, b.zo.ih, box);
    K.tl.to(b.zimg, { width: f.width, height: f.height, left: f.left, top: f.top, duration: d || .6, ease: 'power3.inOut' }, t);
  };
  // an accent frame that lands around part of a block (x, y, w, h in block px)
  K.ring = function (b, o, t, col) {
    const r = K.el(b, 'abs', { left: o.x, top: o.y, width: o.w, height: o.h, borderRadius: '18px', border: `8px solid ${col || K.C.accent}`, zIndex: 5 });
    K.pop(r, t, 1.15); return r;
  };
})();

/* failure and flow moves (no crossed-out icons, no stamps: J4, J7). */
(function () {
  // the block cracks in two along a jagged line and the halves fall apart. Use for "flawed / wrong / broken".
  K.crack = function (b, t, o) {
    o = o || {}; const w = parseFloat(b.style.width), h = parseFloat(b.style.height), par = b.parentNode;
    const cx = o.at || .52, pts = [];
    for (let k = 0; k <= 6; k++) pts.push([(cx + (k % 2 ? .05 : -.05)) * 100, k / 6 * 100]);
    const L = 'polygon(0% 0%, ' + pts.map(p => p[0] + '% ' + p[1] + '%').join(', ') + ', 0% 100%)';
    const R = 'polygon(100% 0%, ' + pts.map(p => p[0] + '% ' + p[1] + '%').join(', ') + ', 100% 100%)';
    const halves = [L, R].map((cp, k) => {
      const hv = K.el(par, 'blk ' + b.className.replace('blk', ''), { left: parseFloat(b.style.left), top: parseFloat(b.style.top), width: w, height: h, borderRadius: b.style.borderRadius, opacity: 0 });
      const f = b.face.cloneNode(true); hv.appendChild(f); hv.style.clipPath = cp; return hv; });
    K.tl.set(halves, { opacity: 1 }, t); K.tl.set(b, { opacity: 0 }, t + .01);
    K.tl.fromTo(halves[0], { x: 0, y: 0, rotation: 0 }, { x: -46, y: 26, rotation: -7, duration: .35, ease: 'power3.out', immediateRender: false }, t);
    K.tl.fromTo(halves[1], { x: 0, y: 0, rotation: 0 }, { x: 46, y: 40, rotation: 8, duration: .35, ease: 'power3.out', immediateRender: false }, t);
    if (o.fall) halves.forEach((hv, k) => K.tl.to(hv, { y: 900, rotation: k ? 30 : -24, duration: .6, ease: 'power2.in' }, t + .5));
    K.shake(par, t, 6); return halves;
  };
  // a block tips over its corner and falls out of the panel (it falls off the stack)
  K.fall = function (b, t, dir) {
    dir = dir || 1;
    K.tl.to(b, { rotation: 14 * dir, duration: .18, ease: 'power2.in', transformOrigin: dir > 0 ? '100% 100%' : '0% 100%' }, t);
    K.tl.to(b, { y: 1000, x: 120 * dir, rotation: 50 * dir, duration: .55, ease: 'power2.in' }, t + .18);
  };
  // an alarm wash on the ground (one onset, slow fade)
  K.alarm = function (t) {
    const a = K.el(document.getElementById('root'), 'abs', { left: 0, top: 0, width: 1080, height: 960, zIndex: 4, opacity: 0,
      background: 'radial-gradient(70% 70% at 50% 50%, transparent 30%, color-mix(in srgb, var(--alarm) 45%, transparent) 100%)' });
    K.tl.fromTo(a, { opacity: 0 }, { opacity: 1, duration: .08, immediateRender: false }, t);
    K.tl.to(a, { opacity: 0, duration: .9, ease: 'power2.out' }, t + .1); return a;
  };
  // a packet (glowing dot) travels a list of points; returns the node
  K.packet = function (parent, pts, t, d, col) {
    const p = K.el(parent, 'abs', { left: pts[0][0] - 18, top: pts[0][1] - 18, width: 36, height: 36, borderRadius: '50%', background: col || K.C.accent,
      boxShadow: `0 0 24px 6px ${col || K.C.accent}`, opacity: 0, zIndex: 30 });
    K.tl.set(p, { opacity: 1 }, t);
    const seg = d / (pts.length - 1);
    pts.slice(1).forEach((q, k) => K.tl.to(p, { left: q[0] - 18, top: q[1] - 18, duration: seg, ease: 'power2.inOut' }, t + k * seg));
    return p;
  };
  // centred kinetic line: words rise from behind a mask, one per cue (the said words; the one exception to J3)
  K.line = function (parent, o) {
    const box = K.el(parent, 'abs disp', { left: 0, width: 1080, top: o.y, textAlign: 'center', fontSize: o.size || 110 });
    const spans = o.words.map((w, k) => { const m = K.el(box, '', { display: 'inline-block', overflow: 'hidden', verticalAlign: 'top', padding: '0 .12em', margin: '0 -.06em' });
      const s = K.el(m, '', { display: 'inline-block', color: o.color && o.color[k] || K.C.onGround }, w); return s; });
    spans.forEach((s, k) => K.tl.fromTo(s, { yPercent: 105 }, { yPercent: 0, duration: .3, ease: 'power3.out', immediateRender: true }, o.t[k] - .1));
    box.spans = spans; return box;
  };
})();
