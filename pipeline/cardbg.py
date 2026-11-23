"""cardbg.py: slow background motions for the textured plate behind an explainer card (R58).

Small graphical motion in the texture keeps a card fresh without overpowering it.
Five motions, all on the GSAP timeline (HyperFrames seeks it frame by frame, so no CSS animations):
  drift  the texture pans and zooms slowly, the card floats a few px
  dots   the halftone dot field drifts on a diagonal and breathes
  edge   the textured edges wipe in from both sides, then breathe
  grain  a soft film-grain flicker (4 noise frames, 15 fps)
  glow   a faint light travels behind the card
LAYERS(style) gives the HTML inside the card box; JS defines CB[style](el, tl, a, b) for a card shown from a to b s.
Assets the page needs next to it: band.png (brand/textures/band.png) and grain_0..3.png (brand/textures/grain/). Colours are brand.css tokens, so a dark or light ground both work.
"""
STYLES = ('drift', 'dots', 'edge', 'grain', 'glow')

CSS = r"""
.hl { position: absolute; inset: 0; overflow: hidden; background: var(--ground); display: flex; align-items: center; justify-content: center; }
.hl .bg-tex { position: absolute; inset: -4%; width: 108%; height: 108%; object-fit: fill; }
.hl .bg-dark { position: absolute; inset: 0; background: radial-gradient(ellipse 52% 46% at 50% 50%, color-mix(in srgb, var(--ground) 85%, transparent) 40%, transparent 100%); }
.hl .bg-dots { position: absolute; inset: -120px; opacity: 0; background-image: radial-gradient(circle, color-mix(in srgb, var(--on-ground) 30%, transparent) 2.4px, transparent 3px); background-size: 22px 22px;
  -webkit-mask-image: radial-gradient(ellipse 75% 70% at 50% 50%, transparent 40%, black 95%); mask-image: radial-gradient(ellipse 75% 70% at 50% 50%, transparent 40%, black 95%); }
.hl .bg-glow { position: absolute; width: 760px; height: 760px; left: 50%; top: 50%; margin: -380px 0 0 -380px; opacity: 0; border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--on-ground) 28%, transparent), transparent 65%); }
.hl .bg-grain { position: absolute; inset: 0; opacity: 0; } .hl .bg-grain.on { opacity: .45; }
.hl .bg-grain img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; mix-blend-mode: var(--grain-blend); filter: var(--grain-filter); }
.hl .card { position: relative; width: 900px; background: var(--paper); color: var(--on-paper); border-radius: 10px; padding: 46px 52px 50px; box-shadow: 0 30px 70px -20px rgba(0,0,0,.8); }
"""


def layers(style):
    grain = ''.join(f'<img src="grain_{k}.png">' for k in range(4))
    return (f'<img class="bg-tex" src="band.png"><div class="bg-dark"></div><div class="bg-dots"></div><div class="bg-glow"></div>'
            f'<div class="bg-grain">{grain}</div>')


JS = r'''
const CB = {
  drift: (el, tl, a, b) => {
    tl.fromTo(el.querySelector('.bg-tex'), {scale: 1, xPercent: 0, yPercent: 0}, {scale: 1.07, xPercent: -1.8, yPercent: -1, duration: b - a, ease: 'none'}, a);
    tl.fromTo(el.querySelector('.card'), {y: 7}, {y: -7, duration: b - a, ease: 'sine.inOut'}, a);
  },
  dots: (el, tl, a, b) => {
    const d = el.querySelector('.bg-dots');
    tl.fromTo(d, {opacity: 0, x: 0, y: 0}, {opacity: .9, duration: .8, ease: 'power2.out'}, a);
    tl.to(d, {x: -66, y: -66, duration: b - a, ease: 'none'}, a);
    for (let t = a + .8; t < b - 1.6; t += 3.2) { tl.to(d, {opacity: .45, duration: 1.6, ease: 'sine.inOut'}, t); tl.to(d, {opacity: .9, duration: 1.6, ease: 'sine.inOut'}, t + 1.6); }
  },
  edge: (el, tl, a, b) => {
    const x = el.querySelector('.bg-tex');
    tl.fromTo(x, {clipPath: 'inset(0% 50% 0% 50%)'}, {clipPath: 'inset(0% 0% 0% 0%)', duration: .9, ease: 'power3.out'}, a);
    for (let t = a + .9; t < b - 2; t += 4) { tl.to(x, {scale: 1.03, duration: 2, ease: 'sine.inOut'}, t); tl.to(x, {scale: 1, duration: 2, ease: 'sine.inOut'}, t + 2); }
  },
  grain: (el, tl, a, b) => {
    const g = el.querySelector('.bg-grain'), im = [...g.querySelectorAll('img')];
    tl.set(g, {opacity: .45}, a);
    let k = 0; for (let t = a; t < b; t += 1 / 15, k++) im.forEach((x, j) => tl.set(x, {opacity: j === k % 4 ? 1 : 0}, t));
    tl.fromTo(el.querySelector('.bg-tex'), {scale: 1}, {scale: 1.03, duration: b - a, ease: 'none'}, a);
  },
  glow: (el, tl, a, b) => {
    const g = el.querySelector('.bg-glow');
    tl.fromTo(g, {opacity: 0, x: -260, y: 90}, {opacity: 1, duration: 1, ease: 'power2.out'}, a);
    tl.to(g, {x: 260, y: -90, duration: b - a, ease: 'sine.inOut'}, a);
  },
};
'''
