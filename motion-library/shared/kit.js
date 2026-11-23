/* Motion library kit. Colours come from brand.css. Deterministic helpers for HyperFrames pages: one paused GSAP timeline at window.__timelines['main'].
   No Math.random, no clocks. Every visual is a function of the timeline. Copied next to every treatment's index.html. */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const K = {};
  const tok = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();   // real colour values: GSAP cannot tween a var()
  K.mix = function (a, b, t) { const p = h => [1, 3, 5].map(k => parseInt(h.slice(k, k + 2), 16)), x = p(a), y = p(b);   // a at share t, the rest b
    return '#' + x.map((v, k) => Math.round(v * t + y[k] * (1 - t)).toString(16).padStart(2, '0')).join(''); };
  K.C = { paper: tok('--paper'), onPaper: tok('--on-paper'), ground: tok('--ground'), onGround: tok('--on-ground'), accent: tok('--accent'), deep: tok('--accent-deep'), alarm: tok('--alarm') };
  K.C.paper2 = K.mix(K.C.paper, K.C.onPaper, .9); K.C.tint = K.mix(K.C.accent, K.C.paper, .25);

  // seeded PRNG (mulberry32)
  K.rng = function (a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; };

  K.timeline = function (dur) {
    const tl = gsap.timeline({ paused: true });
    window.__timelines = window.__timelines || {}; window.__timelines['main'] = tl;
    K.tl = tl; K.DUR = dur; return tl;
  };
  K.finish = function () { K.tl.to({}, { duration: K.DUR }, 0); K.tl.seek(0); };

  K.el = function (parent, cls, css, html) { const e = document.createElement('div'); if (cls) e.className = cls;
    if (css) Object.assign(e.style, css); if (html != null) e.innerHTML = html; parent.appendChild(e); return e; };
  K.svg = function (parent, w, h, cls) { const s = document.createElementNS(NS, 'svg'); s.setAttribute('width', w); s.setAttribute('height', h);
    s.setAttribute('viewBox', `0 0 ${w} ${h}`); s.setAttribute('class', cls || 'layer'); parent.appendChild(s); return s; };
  K.mk = function (parent, tag, attrs) { const e = document.createElementNS(NS, tag); for (const a in attrs) e.setAttribute(a, attrs[a]); parent.appendChild(e); return e; };

  // ground: paper + dot grid + accent glow + seeded grain
  K.ground = function (root, opts) {
    opts = opts || {};
    const g = K.el(root, 'ground'); root.insertBefore(g, root.firstChild); K.el(g, 'dots'); K.el(g, 'glow'); K.el(g, 'vig');
    const c = document.createElement('canvas'); c.className = 'grain'; c.width = 540; c.height = 480; root.appendChild(c);
    const x = c.getContext('2d'), r = K.rng(opts.seed || 11), im = x.createImageData(540, 480);
    for (let i = 0; i < im.data.length; i += 4) { const v = 110 + r() * 145 | 0; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
    x.putImageData(im, 0, 0); Object.assign(c.style, { width: '100%', height: '100%' });
    return g;
  };

  // rounded polyline path
  K.rounded = function (pts, r) {
    let d = `M${pts[0][0]} ${pts[0][1]}`;
    for (let i = 1; i < pts.length - 1; i++) {
      const [ax, ay] = pts[i - 1], [bx, by] = pts[i], [cx, cy] = pts[i + 1];
      const l1 = Math.hypot(bx - ax, by - ay), l2 = Math.hypot(cx - bx, cy - by), rr = Math.min(r, l1 / 2, l2 / 2);
      const p1 = [bx - (bx - ax) / l1 * rr, by - (by - ay) / l1 * rr], p2 = [bx + (cx - bx) / l2 * rr, by + (cy - by) / l2 * rr];
      d += ` L${p1[0]} ${p1[1]} Q${bx} ${by} ${p2[0]} ${p2[1]}`;
    }
    const e = pts[pts.length - 1]; return d + ` L${e[0]} ${e[1]}`;
  };

  // a path draws itself: dash offset tween
  K.draw = function (path, t, dur, ease) {
    const L = path.getTotalLength(); path.setAttribute('stroke-dasharray', `${L} ${L}`); path.setAttribute('stroke-dashoffset', L);
    K.tl.to(path, { attr: { 'stroke-dashoffset': 0 }, duration: dur, ease: ease || 'power2.inOut' }, t); return L;
  };

  // numbers: proxy tween with onUpdate (never set textContent through gsap.set)
  K.count = function (node, t, from, to, dur, fmt, ease) {
    const o = { v: from }; node.textContent = fmt(from);
    K.tl.to(o, { v: to, duration: dur, ease: ease || 'expo.out', onUpdate: () => { const s = fmt(o.v); if (node.textContent !== s) node.textContent = s; } }, t);
  };
  K.fmt = { plain: v => Math.round(v).toLocaleString('en-US'), money: v => '$' + Math.round(v).toLocaleString('en-US'), int: v => String(Math.round(v)) };

  // landings: from 0.6 to 0.9 scale with opacity, never from 0
  K.land = function (node, t, from, dur, ease) {
    K.tl.fromTo(node, Object.assign({ opacity: 0, scale: .82, y: 40 }, from || {}), { opacity: 1, scale: 1, y: 0, x: 0, rotation: 0, duration: dur || .55, ease: ease || 'back.out(1.7)' }, t);
  };
  K.rise = function (node, t, dy, dur) { K.tl.fromTo(node, { opacity: 0, y: dy || 24 }, { opacity: 1, y: 0, duration: dur || .4, ease: 'power3.out' }, t); };

  // arrival pulse: a ring expands and fades, the target gives a small kick
  K.pulse = function (parent, cx, cy, r, t, color, width) {
    const ring = K.el(parent, 'ring', { left: (cx - r) + 'px', top: (cy - r) + 'px', width: 2 * r + 'px', height: 2 * r + 'px', borderColor: color || K.C.deep, borderWidth: (width || 8) + 'px' });
    K.tl.fromTo(ring, { opacity: .95, scale: .9 }, { opacity: 0, scale: 1.45, duration: .8, ease: 'power2.out', immediateRender: false }, t);
    K.tl.set(ring, { opacity: 0 }, 0);
    return ring;
  };
  K.kick = function (node, t, amt) { K.tl.to(node, { scale: 1 + (amt || .04), duration: .09, ease: 'power2.out' }, t); K.tl.to(node, { scale: 1, duration: .5, ease: 'back.out(3)' }, t + .09); };
  K.shake = function (node, t, amp, n) { const a = amp || 14; n = n || 5; for (let i = 0; i < n; i++) K.tl.to(node, { x: (i % 2 ? -1 : 1) * a * (1 - i / n), duration: .05, ease: 'sine.inOut' }, t + i * .05);
    K.tl.to(node, { x: 0, duration: .08, ease: 'sine.out' }, t + n * .05); };

  // sample a path into a lookup so packets can ride it
  K.sampler = function (path, n) {
    n = n || 400; const L = path.getTotalLength(), P = [];
    for (let i = 0; i <= n; i++) { const q = path.getPointAtLength(L * i / n); P.push([q.x, q.y]); }
    return { L, at: u => { const f = Math.max(0, Math.min(n, u * n)), i = Math.min(n - 1, Math.floor(f)), r = f - i;
      return [P[i][0] + (P[i + 1][0] - P[i][0]) * r, P[i][1] + (P[i + 1][1] - P[i][1]) * r]; } };
  };
  // packet: a dot with a comet trail rides a path from t over dur
  K.packet = function (parent, path, t, dur, color, size, ease) {
    const s = K.sampler(path), sz = size || 34;
    const dot = K.el(parent, 'abs', { left: 0, top: 0, width: sz + 'px', height: sz + 'px', marginLeft: -sz / 2 + 'px', marginTop: -sz / 2 + 'px', borderRadius: '50%',
      background: color || K.C.deep, border: '6px solid var(--paper)', boxShadow: `0 6px 16px color-mix(in srgb, ${color || K.C.deep} 45%, transparent)`, opacity: 0 });
    const pr = { u: 0 };
    K.tl.to(pr, { u: 1, duration: dur, ease: ease || 'power2.inOut', onUpdate: () => { const p = s.at(pr.u); dot.style.transform = `translate(${p[0]}px,${p[1]}px)`;
      dot.style.opacity = pr.u > 0 && pr.u < 1 ? 1 : 0; } }, t);
    return dot;
  };

  // a pure function of time for anything that is easier to draw than to tween
  K.every = function (fn, t0, t1) { const p = { t: t0 }; fn(t0); K.tl.fromTo(p, { t: t0 }, { t: t1, duration: t1 - t0, ease: 'none', onUpdate: () => fn(p.t), immediateRender: false }, t0); };

  // standard exit: the whole hero lifts and fades (hard cut friendly)
  K.exit = function (node, t, dur) { K.tl.to(node, { opacity: 0, y: -30, scale: .97, duration: dur || .35, ease: 'power2.in' }, t); };

  window.K = K;
})();
