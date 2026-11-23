// Sample run: a number lands on the word that says it. c(src) = word start by episode word number. ci(i) = by clip word index. ce(src) = word end.
const s = K.scene(0, null);
const tile = K.block(s, { x: 180, y: 250, w: 720, h: 420, r: 44, cls: 'paper' });
tile.face.insertAdjacentHTML('beforeend', '<div class="disp" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:150px;color:var(--on-paper)">3x</div>');
K.drop(tile, 0);
K.kick(tile, c(28), .06);
