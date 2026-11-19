/* 01_core.js : données, formats, statistiques, calcul de g, tests A et B (mêmes règles que a14_backtest.py) */
(function () {
  const R = window.RDCF, M = R.meta, COLS = M.cols;
  const A = (window.A = { R, M, state: { r: 0.09, prime: 0.05, ecart: 0.015, mode: 'wacc', cyc: true, rShow: null, univ: 'membres' }, pages: {}, YEARS: [] });

  // ---------- données ----------
  A.comp = R.companies.map((c, i) => ({ i, t: c[0], cik: c[1], bloc: c[2], cat: c[3], sic: c[4], sicd: c[5], src: c[6], rows: [] }));
  A.rows = R.rows.map(r => {
    const o = {};
    COLS.forEach((c, i) => (o[c] = r[i]));
    const co = A.comp[o.c];
    o.co = co; o.t = co.t; o.bloc = co.bloc; o.cat = co.cat; o.cik = co.cik;
    o.spn = M.statuts_prix[o.sp];
    o.sgn = o.sg == null ? null : M.statuts_g[o.sg];
    o.dsn = o.ds == null ? null : M.statuts_dette[o.ds];
    o.g = null; o.ecart = null; o.reff = null;
    co.rows.push(o);
    return o;
  });
  A.byTicker = {};
  A.comp.forEach(c => (A.byTicker[c.t] = c));
  A.BLOCS = Array.from(new Set(A.comp.map(c => c.bloc))).sort((a, b) => a.localeCompare(b, 'fr'));
  A.YEARS = Array.from(new Set(A.rows.map(r => r.a))).sort((a, b) => a - b);
  A.Y0 = A.YEARS[0]; A.Y1 = A.YEARS[A.YEARS.length - 1];
  A.blocLabel = b => (b || '').replace('Conso de base', 'Consommation de base').replace('Conso discretionnaire', 'Consommation discrétionnaire').replace('Sante', 'Santé').replace('Matieres et energie', 'Matières et énergie').replace('Materiel tech', 'Matériel tech').replace('Telecom et medias', 'Télécom et médias');

  // ---------- g selon r (même formule que a12) ----------
  // WACC de marché : E/V x (taux 10 ans + prime) + D/V x (taux 10 ans + écart de crédit) x (1 - impôt) ; E/V et D/V par année (meta.wacc), taux 10 ans par ligne (colonne t10)
  A.imp = y => (y <= 2017 ? 0.35 : 0.21);
  A.waccOf = (o, prime, ecart) => { const w = A.M.wacc[o.a]; return w && o.t10 != null ? w[0] * (o.t10 + prime) + w[1] * (o.t10 + ecart) * (1 - A.imp(o.a)) : null; };
  A.recompute = function () {
    const cyc = A.state.cyc, fx = A.state.mode === 'fixe', rv = [];
    for (const o of A.rows) {
      const base = fx ? A.state.r : A.waccOf(o, A.state.prime, A.state.ecart);
      const rr = base == null ? null : base + (cyc && o.cat === 'Cyclique' ? 0.01 : 0);
      o.reff = rr;
      o.g = o.sg === 0 && o.ve != null && o.fcfr != null && rr != null ? (o.ve * rr - o.fcfr) / (o.ve + o.fcfr) : null;
      o.ecart = o.g != null && o.gr != null ? o.gr - o.g : null;
      if (o.g != null) rv.push(rr);
    }
    rv.sort((x, y) => x - y);
    A.state.rShow = rv.length ? rv[Math.floor(rv.length / 2)] : null;
  };
  A.rTxt = () => (A.state.mode === 'fixe' ? 'r fixe = ' + A.pc(A.state.r) : 'WACC de marché (prime de risque ' + A.pc(A.state.prime) + ', WACC médian ' + A.pc(A.state.rShow) + ')');
  A.gOf = (ve, fcf, r) => (ve * r - fcf) / (ve + fcf);

  // ---------- formats ----------
  const esc = (A.esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])));
  A.nf = (v, d = 1) => (v == null || !isFinite(v) ? '–' : v.toLocaleString('fr-FR', { minimumFractionDigits: d, maximumFractionDigits: d }).replace('-', '−').replace(/^−(0(,0+)?)$/, '$1'));
  A.pc = (v, d = 1) => (v == null || !isFinite(v) ? '–' : A.nf(v * 100, d) + ' %');
  A.pts = (v, d = 1) => (v == null || !isFinite(v) ? '–' : (v > 0.0005 ? '+' : '') + A.nf(v * 100, d) + ' pts');
  A.sp = (v, d = 1) => (v == null || !isFinite(v) ? '–' : (v > 0.5 * Math.pow(10, -d - 2) ? '+' : '') + A.nf(v * 100, d) + ' %');
  A.fM = (v, d = 1) => (v == null ? '–' : Math.abs(v) >= 1000 ? A.nf(v / 1000, d) + ' Md$' : A.nf(v, 0) + ' M$');
  A.fMd = (v, d = 1) => (v == null ? '–' : A.nf(v / 1000, d)); // milliards, sans unité
  A.usd = (v, d = 2) => (v == null ? '–' : '$' + A.nf(v, d));
  A.dateFr = s => (s ? s.slice(8, 10) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4) : '–');

  // ---------- statistiques ----------
  A.sum = a => a.reduce((x, y) => x + y, 0);
  A.mean = a => (a.length ? A.sum(a) / a.length : null);
  A.quantile = (a, p) => {
    if (!a.length) return null;
    const s = a.slice().sort((x, y) => x - y), k = (s.length - 1) * p, f = Math.floor(k), c = Math.ceil(k);
    return s[f] + (s[c] - s[f]) * (k - f);
  };
  A.median = a => A.quantile(a, 0.5);
  A.ranks = a => {
    const idx = a.map((v, i) => [v, i]).sort((x, y) => x[0] - y[0]), r = new Array(a.length);
    for (let i = 0; i < idx.length;) {
      let j = i;
      while (j + 1 < idx.length && idx[j + 1][0] === idx[i][0]) j++;
      const avg = (i + j) / 2 + 1;
      for (let k = i; k <= j; k++) r[idx[k][1]] = avg;
      i = j + 1;
    }
    return r;
  };
  A.pearson = (x, y) => {
    const n = x.length;
    if (n < 3) return null;
    const mx = A.mean(x), my = A.mean(y);
    let sxy = 0, sxx = 0, syy = 0;
    for (let i = 0; i < n; i++) { const dx = x[i] - mx, dy = y[i] - my; sxy += dx * dy; sxx += dx * dx; syy += dy * dy; }
    return sxx && syy ? sxy / Math.sqrt(sxx * syy) : null;
  };
  A.spearman = (x, y) => A.pearson(A.ranks(x), A.ranks(y));
  A.groupBy = (list, f) => { const m = new Map(); for (const o of list) { const k = f(o); if (!m.has(k)) m.set(k, []); m.get(k).push(o); } return m; };

  // ---------- univers : sociétés membres du S&P 500 à la date de clôture (par CIK), hors indice, ou toutes ----------
  A.univOf = o => (o.mb === 1 ? 'membres' : 'hors indice');
  A.inUniv = (list, u) => { u = u || A.state.univ; return u === 'tous' ? list : list.filter(o => A.univOf(o) === u); };

  // ---------- test A (croissance réelle du FCFF contre g implicite) ----------
  A.testA = function (list, univ) {
    const L = A.inUniv(list, univ).filter(o => o.g != null && o.gr != null);
    if (!L.length) return { n: 0 };
    const g = L.map(o => o.g), gr = L.map(o => o.gr), ec = L.map(o => o.gr - o.g);
    return { n: L.length, gMed: A.median(g), grMed: A.median(gr), ecMed: A.median(ec), prudent: ec.filter(v => v > 0).length / L.length, rho: A.spearman(g, gr), rows: L };
  };

  // ---------- test B (quartiles de FCF/VE, rendement en excès) : mêmes règles que a14 ----------
  // Q1 = g le plus bas = FCF/VE le plus haut. Le rendement en excès est calculé contre la médiane de l'année dans l'univers choisi.
  A.MIN_BLOC_ANNEE = 8; A.MIN_ANNEE = 100;
  A.assignQuartiles = function (list, keyFn, minN) {
    const out = [];
    for (const [, grp] of A.groupBy(list, keyFn)) {
      const n = grp.length;
      if (n < minN) continue;
      const s = grp.slice().sort((a, b) => b.fcfr / b.ve - a.fcfr / a.ve), e1 = 1 + (n - 1) * 0.25, e2 = 1 + (n - 1) * 0.5, e3 = 1 + (n - 1) * 0.75;
      s.forEach((o, i) => { const k = i + 1; out.push([o, k <= e1 ? 0 : k <= e2 ? 1 : k <= e3 ? 2 : 3]); });
    }
    return out;
  };
  A._med = {};
  A.excMed = function (univ) {
    if (A._med[univ]) return A._med[univ];
    const L = univ === 'tous' ? A.rows : A.rows.filter(o => A.univOf(o) === univ), out = { r1: {}, r3: {} };
    // rendements limites aux percentiles 1 % et 99 % de chaque année (comme a14, interpolation linéaire), puis médiane des rendements limités
    const quant = (v, p) => { const i = (v.length - 1) * p, j = Math.floor(i); return j + 1 < v.length ? v[j] + (v[j + 1] - v[j]) * (i - j) : v[j]; };
    for (const k of ['r1', 'r3']) for (const [y, grp] of A.groupBy(L.filter(o => o[k] != null), o => o.a)) {
      const v = grp.map(o => o[k]).sort((a, b) => a - b), lo = quant(v, 0.01), hi = quant(v, 0.99);
      out[k][y] = { lo, hi, med: A.median(v.map(x => Math.min(hi, Math.max(lo, x)))) };
    }
    return (A._med[univ] = out);
  };
  A.testB = function (list, minAnnee, univ) {
    univ = univ || A.state.univ;
    const base = A.inUniv(list, univ), med = A.excMed(univ), mn = minAnnee == null ? A.MIN_ANNEE : minAnnee, res = {};
    for (const h of [1, 3]) {
      const k = 'r' + h, B = base.filter(o => o.g != null && o[k] != null && o.fcfr != null && o.ve), ex = o => { const m = med[k][o.a]; return Math.min(m.hi, Math.max(m.lo, o[k])) - m.med; };
      const qb = A.assignQuartiles(B, o => o.bloc + '|' + o.a, A.MIN_BLOC_ANNEE);
      const quart = [0, 1, 2, 3].map(q => { const L = qb.filter(x => x[1] === q); return { n: L.length, x: A.mean(L.map(x => ex(x[0]))) }; });
      const qy = A.assignQuartiles(B, o => o.a, mn), years = new Map();
      for (const y of A.YEARS) {
        const L = qy.filter(x => x[0].a === y);
        if (!L.length) continue;
        const m = q => A.mean(L.filter(x => x[1] === q).map(x => ex(x[0])));
        years.set(y, { n: L.length, q1: m(0), q4: m(3) });
      }
      res[h] = { n: B.length, quart, years };
    }
    const quart = [0, 1, 2, 3].map(q => ({ q, n: res[1].quart[q].n, n3: res[3].quart[q].n, x1: res[1].quart[q].x, x3: res[3].quart[q].x }));
    const years = [];
    for (const y of A.YEARS) {
      const a = res[1].years.get(y), b = res[3].years.get(y);
      if (!a && !b) continue;
      years.push({ a: y, n: a ? a.n : null, n3: b ? b.n : null, q1x1: a ? a.q1 : null, q4x1: a ? a.q4 : null, s1: a ? a.q1 - a.q4 : null, q1x3: b ? b.q1 : null, q4x3: b ? b.q4 : null, s3: b ? b.q1 - b.q4 : null });
    }
    return { nB: res[1].n, nB3: res[3].n, quart, years };
  };
  // nombre d'années où Q1 gagne, sur le nombre d'années testées (k = 's1' ou 's3')
  A.winCount = (tb, k) => { const L = tb.years.filter(y => y[k] != null); return [L.filter(y => y[k] > 0).length, L.length]; };

  // ---------- infobulle ----------
  const tip = () => document.getElementById('tip');
  A.showTip = (e, html) => {
    const t = tip(); t.innerHTML = html; t.style.opacity = 1;
    const w = t.offsetWidth, h = t.offsetHeight; let x = e.clientX + 14, y = e.clientY - h - 10;
    if (x + w > innerWidth - 8) x = e.clientX - w - 14; if (y < 8) y = e.clientY + 16;
    t.style.left = x + 'px'; t.style.top = y + 'px';
  };
  A.hideTip = () => { tip().style.opacity = 0; };
  A.tipOn = (el, f) => { el.addEventListener('pointermove', e => { const h = f(e); if (h) A.showTip(e, h); else A.hideTip(); }); el.addEventListener('pointerleave', A.hideTip); };

  // ---------- divers ----------
  A.$ = id => document.getElementById(id);
  A.csv = (name, header, lines) => {
    const q = v => { const s = v == null ? '' : typeof v === 'number' ? String(+v.toFixed(6)).replace('.', ',') : String(v); return /[",;\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
    const txt = '﻿' + [header].concat(lines).map(l => l.map(q).join(';')).join('\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([txt], { type: 'text/csv;charset=utf-8' })); a.download = name; document.body.appendChild(a); a.click(); a.remove();
  };
  A.link = t => '<a href="#/entreprise/' + encodeURIComponent(t) + '">' + esc(t) + '</a>';
  A.recompute();
})();
