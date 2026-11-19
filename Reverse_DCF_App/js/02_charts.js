/* 02_charts.js : graphiques en SVG, sans bibliothèque (l'appli marche hors connexion) */
(function () {
  const A = window.A;
  const niceTicks = (lo, hi, k) => {
    const span = hi - lo || 1, raw = span / k, p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p, s = (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p, t = [];
    for (let v = Math.ceil(lo / s - 1e-9) * s; v <= hi + 1e-9; v += s) t.push(+v.toFixed(10));
    return t;
  };
  A.niceTicks = niceTicks;
  const width = el => Math.max(300, el.clientWidth || 600);

  /* courbes, barres, anneaux, pointillés, bandes, par année */
  A.lineChart = function (el, o) {
    const W = width(el), H = o.h || 150, m = { l: o.ml || 44, r: o.mr || 14, t: o.mt || 16, b: 22 }, n = o.xs.length;
    const vals = o.series.flatMap(s => [].concat(s.v || [], s.lo || [], s.hi || [])).filter(v => v != null && isFinite(v));
    if (!vals.length || n === 0) { el.innerHTML = '<div class="empty">Pas de données pour ce graphique.</div>'; return; }
    let lo = Math.min(...vals), hi = Math.max(...vals);
    if (o.zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
    const pad = (hi - lo) * 0.1 || 1;
    if (!(o.zero && lo === 0)) lo -= pad; hi += pad;
    const bw = (W - m.l - m.r) / n, X = i => m.l + (i + 0.5) * bw, Y = v => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${A.esc(o.label || '')}">`;
    niceTicks(lo, hi, 3).forEach(t => { s += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(t)}" y2="${Y(t)}" stroke="${Math.abs(t) < 1e-12 ? 'var(--axis)' : 'var(--grid)'}"/><text x="${m.l - 6}" y="${Y(t) + 4}" text-anchor="end">${o.yfmt(t)}</text>`; });
    const step = n > 18 ? 5 : n > 8 ? 2 : 1;
    o.xs.forEach((x, i) => { if (i % step === 0) s += `<text x="${X(i)}" y="${H - 6}" text-anchor="middle">${x}</text>`; });
    const si = o.xs.indexOf(o.sel);
    if (si >= 0) s += `<rect x="${X(si) - bw / 2}" y="${m.t - 6}" width="${bw}" height="${H - m.t - m.b + 6}" fill="var(--s2)" opacity=".10"/><text x="${X(si)}" y="${H - 6}" text-anchor="middle" style="fill:var(--ink);font-weight:700">${o.sel}</text>`;
    o.series.forEach(se => {
      if (se.kind === 'band') {
        let up = '', dn = [];
        se.hi.forEach((v, i) => { if (v != null && se.lo[i] != null) { up += (up ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1); dn.push('L' + X(i).toFixed(1) + ' ' + Y(se.lo[i]).toFixed(1)); } });
        if (up) s += `<path d="${up}${dn.reverse().join('')}Z" fill="${se.color}" opacity=".16"/>`;
      }
      if (se.kind === 'bar') se.v.forEach((v, i) => { if (v == null) return; const y0 = Y(0), y1 = Y(v), w = Math.min(18, bw * 0.62); s += `<rect x="${X(i) - w / 2}" y="${Math.min(y0, y1)}" width="${w}" height="${Math.max(1, Math.abs(y1 - y0))}" rx="2" fill="${se.colorFn ? se.colorFn(v) : se.color}" opacity="${i === si ? 1 : 0.88}"/>`; });
      if (se.kind === 'line' || se.kind === 'dash') {
        let d = '', on = false;
        se.v.forEach((v, i) => { if (v == null) { on = false; return; } d += (on ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1); on = true; });
        s += `<path d="${d}" fill="none" stroke="${se.color}" stroke-width="2" ${se.kind === 'dash' ? 'stroke-dasharray="5 4" opacity=".85"' : ''} stroke-linejoin="round" stroke-linecap="round"/>`;
        if (se.kind === 'line' && n <= 20) se.v.forEach((v, i) => { if (v != null) s += `<circle cx="${X(i)}" cy="${Y(v)}" r="2.2" fill="${se.color}"/>`; });
      }
      if (se.kind === 'ring') se.v.forEach((v, i) => { if (v != null) s += `<circle cx="${X(i)}" cy="${Y(v)}" r="4.5" fill="var(--surface)" stroke="${se.color}" stroke-width="2"/>`; });
      if (si >= 0 && se.v && se.v[si] != null && se.kind !== 'dash' && se.kind !== 'band') {
        const v = se.v[si];
        if (se.kind === 'line') s += `<circle cx="${X(si)}" cy="${Y(v)}" r="5" fill="${se.color}" stroke="var(--surface)" stroke-width="2"/>`;
        if (se.label) s += `<text class="val" x="${Math.min(W - m.r - 2, Math.max(m.l + 2, X(si)))}" y="${Y(v) + (v >= 0 ? -9 : 16)}" text-anchor="middle">${se.label(v)}</text>`;
      }
    });
    s += `<rect class="hit" x="${m.l}" y="0" width="${W - m.l - m.r}" height="${H}" fill="transparent" style="cursor:${o.onSel ? 'pointer' : 'default'}"/></svg>`;
    el.innerHTML = s;
    const hit = el.querySelector('.hit'), idx = e => { const r = hit.getBoundingClientRect(); return Math.max(0, Math.min(n - 1, Math.floor((e.clientX - r.left) / r.width * n))); };
    if (o.tip) A.tipOn(hit, e => o.tip(idx(e)));
    if (o.onSel) hit.addEventListener('click', e => o.onSel(o.xs[idx(e)]));
  };

  /* nuage de points : un point par ligne (entreprise, année) */
  A.scatter = function (el, o) {
    const W = width(el), H = o.h || 380, m = { l: 52, r: 14, t: 12, b: 34 };
    const X = v => m.l + (Math.min(o.xhi, Math.max(o.xlo, v)) - o.xlo) / (o.xhi - o.xlo) * (W - m.l - m.r);
    const Y = v => m.t + (1 - (Math.min(o.yhi, Math.max(o.ylo, v)) - o.ylo) / (o.yhi - o.ylo)) * (H - m.t - m.b);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${A.esc(o.label || '')}">`;
    niceTicks(o.ylo, o.yhi, 5).forEach(t => { s += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(t)}" y2="${Y(t)}" stroke="${Math.abs(t) < 1e-12 ? 'var(--axis)' : 'var(--grid)'}"/><text x="${m.l - 6}" y="${Y(t) + 4}" text-anchor="end">${o.yfmt(t)}</text>`; });
    niceTicks(o.xlo, o.xhi, 7).forEach(t => { s += `<line y1="${m.t}" y2="${H - m.b}" x1="${X(t)}" x2="${X(t)}" stroke="${Math.abs(t) < 1e-12 ? 'var(--axis)' : 'var(--grid)'}"/><text x="${X(t)}" y="${H - m.b + 15}" text-anchor="middle">${o.xfmt(t)}</text>`; });
    s += `<text x="${(m.l + W - m.r) / 2}" y="${H - 3}" text-anchor="middle" style="fill:var(--ink2)">${A.esc(o.xtitle || '')}</text>`;
    s += `<text transform="translate(12 ${(m.t + H - m.b) / 2}) rotate(-90)" text-anchor="middle" style="fill:var(--ink2)">${A.esc(o.ytitle || '')}</text>`;
    const d0 = Math.max(o.xlo, o.ylo), d1 = Math.min(o.xhi, o.yhi);
    s += `<line x1="${X(d0)}" y1="${Y(d0)}" x2="${X(d1)}" y2="${Y(d1)}" stroke="var(--ink2)" stroke-width="1.5" stroke-dasharray="6 4"/>`;
    const px = [];
    let dots = '';
    o.pts.forEach(p => {
      const cx = X(p.x), cy = Y(p.y), clamped = p.x < o.xlo || p.x > o.xhi || p.y < o.ylo || p.y > o.yhi;
      px.push([cx, cy, p]);
      dots += clamped ? `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="3.4" fill="none" stroke="var(--s1)" stroke-width="1.2" opacity=".7"/>` : `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="2.6" fill="var(--s1)" opacity=".30"/>`;
    });
    s += dots;
    if (o.deciles && o.deciles.length) {
      let d = '';
      o.deciles.forEach((q, i) => { d += (i ? 'L' : 'M') + X(q.x).toFixed(1) + ' ' + Y(q.y).toFixed(1); s += `<line x1="${X(q.x)}" x2="${X(q.x)}" y1="${Y(q.lo)}" y2="${Y(q.hi)}" stroke="var(--ink)" stroke-width="1.5" opacity=".55"/>`; });
      s += `<path d="${d}" fill="none" stroke="var(--ink)" stroke-width="2.4"/>`;
      o.deciles.forEach(q => { s += `<circle cx="${X(q.x)}" cy="${Y(q.y)}" r="4.6" fill="var(--s2)" stroke="var(--surface)" stroke-width="2"/>`; });
    }
    s += `<circle id="scHi" r="6" fill="none" stroke="var(--ink)" stroke-width="2" style="display:none"/><rect class="hit" x="${m.l}" y="${m.t}" width="${W - m.l - m.r}" height="${H - m.t - m.b}" fill="transparent" style="cursor:pointer"/></svg>`;
    el.innerHTML = s;
    const svg = el.querySelector('svg'), hit = el.querySelector('.hit'), hi = el.querySelector('#scHi');
    const near = e => {
      const r = svg.getBoundingClientRect(), k = W / r.width, x = (e.clientX - r.left) * k, y = (e.clientY - r.top) * k;
      let best = null, bd = 15 * 15;
      for (const q of px) { const dx = q[0] - x, dy = q[1] - y, dd = dx * dx + dy * dy; if (dd < bd) { bd = dd; best = q; } }
      return best;
    };
    hit.addEventListener('pointermove', e => { const q = near(e); if (q) { hi.setAttribute('cx', q[0]); hi.setAttribute('cy', q[1]); hi.style.display = ''; A.showTip(e, o.tip(q[2])); } else { hi.style.display = 'none'; A.hideTip(); } });
    hit.addEventListener('pointerleave', () => { hi.style.display = 'none'; A.hideTip(); });
    hit.addEventListener('click', e => { const q = near(e); if (q && o.onPick) o.onPick(q[2]); });
  };

  /* histogramme */
  A.hist = function (el, o) {
    const W = width(el), H = o.h || 190, m = { l: 40, r: 12, t: 12, b: 26 }, bins = o.bins;
    const cnt = new Array(bins.length - 1).fill(0);
    o.values.forEach(v => { for (let i = 0; i < cnt.length; i++) { if ((v >= bins[i] && v < bins[i + 1]) || (i === cnt.length - 1 && v >= bins[i + 1]) || (i === 0 && v < bins[0])) { cnt[i]++; break; } } });
    const mx = Math.max(1, ...cnt), bw = (W - m.l - m.r) / cnt.length, Y = v => m.t + (1 - v / mx) * (H - m.t - m.b);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${A.esc(o.label || '')}">`;
    niceTicks(0, mx, 3).forEach(t => { s += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(t)}" y2="${Y(t)}" stroke="var(--grid)"/><text x="${m.l - 6}" y="${Y(t) + 4}" text-anchor="end">${A.nf(t, 0)}</text>`; });
    cnt.forEach((c, i) => { s += `<rect x="${m.l + i * bw + 1}" y="${Y(c)}" width="${Math.max(1, bw - 2)}" height="${H - m.b - Y(c)}" rx="2" fill="var(--s2)" opacity=".85" data-i="${i}"/>`; if (i % o.every === 0) s += `<text x="${m.l + i * bw}" y="${H - 9}" text-anchor="middle">${o.fmt(bins[i])}</text>`; });
    if (o.median != null) { const xm = m.l + ((Math.min(bins[bins.length - 1], Math.max(bins[0], o.median)) - bins[0]) / (bins[bins.length - 1] - bins[0])) * (W - m.l - m.r); s += `<line x1="${xm}" x2="${xm}" y1="${m.t}" y2="${H - m.b}" stroke="var(--ink)" stroke-width="2" stroke-dasharray="4 3"/><text class="val" x="${xm + 4}" y="${m.t + 10}">médiane ${o.fmt(o.median)}</text>`; }
    s += '</svg>'; el.innerHTML = s;
    el.querySelectorAll('rect[data-i]').forEach(r => A.tipOn(r, () => { const i = +r.dataset.i; return `<b>${o.fmt(bins[i])} à ${o.fmt(bins[i + 1])}</b><br>${A.nf(cnt[i], 0)} lignes`; }));
  };

  /* mini courbe pour les cartes */
  A.spark = function (series, years, w, h) {
    const vals = series.flatMap(s => s.v).filter(v => v != null);
    if (!vals.length) return '';
    let lo = Math.min(...vals, 0), hi = Math.max(...vals); const pad = (hi - lo) * 0.1 || 0.01; hi += pad;
    const X = i => 4 + i * (w - 8) / Math.max(1, years.length - 1), Y = v => 4 + (1 - (v - lo) / (hi - lo)) * (h - 8);
    let s = `<svg viewBox="0 0 ${w} ${h}" style="height:${h}px" aria-hidden="true"><line x1="0" x2="${w}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--axis)"/>`;
    series.forEach(se => { let d = '', on = false; se.v.forEach((v, i) => { if (v == null) { on = false; return; } d += (on ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1); on = true; }); s += `<path d="${d}" fill="none" stroke="${se.color}" stroke-width="${se.w || 2}" ${se.dash ? 'stroke-dasharray="4 3"' : ''}/>`; });
    return s + '</svg>';
  };

  /* bande horizontale : toutes les sociétés d'un bloc, une année, la société choisie en évidence */
  A.strip = function (el, o) {
    const W = width(el), H = 74, m = { l: 14, r: 14 };
    const vals = o.values.slice().sort((a, b) => a - b);
    if (!vals.length) { el.innerHTML = ''; return; }
    const lo = Math.min(A.quantile(vals, 0.02), o.mine != null ? o.mine : Infinity, 0), hi = Math.max(A.quantile(vals, 0.98), o.mine != null ? o.mine : -Infinity), X = v => m.l + (Math.min(hi, Math.max(lo, v)) - lo) / (hi - lo) * (W - m.l - m.r);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${A.esc(o.label || '')}"><line x1="${m.l}" x2="${W - m.r}" y1="46" y2="46" stroke="var(--axis)"/>`;
    niceTicks(lo, hi, 6).forEach(t => { s += `<line x1="${X(t)}" x2="${X(t)}" y1="${Math.abs(t) < 1e-12 ? 8 : 43}" y2="49" stroke="${Math.abs(t) < 1e-12 ? 'var(--ink2)' : 'var(--axis)'}"/><text x="${X(t)}" y="64" text-anchor="middle">${A.pc(t, 0)}</text>`; });
    vals.forEach((v, i) => { const jy = 46 - 6 - ((i * 37) % 7) * 3.2; s += `<circle cx="${X(v).toFixed(1)}" cy="${jy}" r="3" fill="var(--s1)" opacity=".35"/>`; });
    const med = A.median(vals); s += `<line x1="${X(med)}" x2="${X(med)}" y1="14" y2="46" stroke="var(--ink2)" stroke-dasharray="3 3"/><text x="${X(med)}" y="10" text-anchor="middle">médiane ${A.pc(med)}</text>`;
    if (o.mine != null) s += `<circle cx="${X(o.mine)}" cy="46" r="6.5" fill="var(--s2)" stroke="var(--surface)" stroke-width="2"/><text class="val" x="${X(o.mine)}" y="36" text-anchor="middle">${A.esc(o.name)} ${A.pc(o.mine)}</text>`;
    el.innerHTML = s + '</svg>';
  };

  /* haltères : g implicite médian et croissance réelle médiane, par bloc */
  A.dumbbell = function (el, lines) {
    const all = lines.flatMap(l => [l.a, l.b]).filter(v => v != null);
    if (!all.length) { el.innerHTML = '<div class="empty">Pas de données.</div>'; return; }
    const lo = Math.min(-0.01, ...all) - 0.005, hi = Math.max(0.12, ...all) + 0.005, P = v => ((v - lo) / (hi - lo) * 100).toFixed(2) + '%';
    el.innerHTML = lines.map((l, i) => `<div class="dr" data-i="${i}"><span>${A.esc(l.name)}</span><div class="trk"><i class="z" style="left:${P(0)}"></i><i class="seg" style="left:${P(Math.min(l.a, l.b))};width:calc(${P(Math.max(l.a, l.b))} - ${P(Math.min(l.a, l.b))})"></i><i class="d" style="left:${P(l.a)};background:var(--s2)"></i><i class="d" style="left:${P(l.b)};background:var(--s3)"></i></div><span class="c">${A.sp(l.ec, 1)}</span><span class="c">ρ = ${A.nf(l.rho, 2)}</span></div>`).join('');
    el.querySelectorAll('.dr').forEach(e => A.tipOn(e, () => lines[+e.dataset.i].tip));
  };
})();
