/* 04 : pages Marché, Blocs, Backtest */
(function () {
  const A = window.A, $ = A.$, esc = A.esc, nf = A.nf, pc = A.pc, sp = A.sp, fM = A.fM;
  A.atPrime = (p, cyc, f) => { const s = [A.state.prime, A.state.mode, A.state.cyc]; A.state.prime = p; A.state.mode = 'wacc'; A.state.cyc = cyc; A.recompute(); try { return f(); } finally { [A.state.prime, A.state.mode, A.state.cyc] = s; A.recompute(); } };
  A.atR = (r, cyc, f) => { const s = [A.state.r, A.state.mode, A.state.cyc]; A.state.r = r; A.state.mode = 'fixe'; A.state.cyc = cyc; A.recompute(); try { return f(); } finally { [A.state.r, A.state.mode, A.state.cyc] = s; A.recompute(); } };
  const opt = (v, t, cur) => `<option value="${esc(v)}"${String(v) === String(cur) ? ' selected' : ''}>${esc(t)}</option>`;
  const gotoCo = o => { A.ps.ent = { t: o.t, year: o.a }; location.hash = '#/entreprise/' + encodeURIComponent(o.t); };
  const heatBg = v => v == null ? '' : `background:color-mix(in srgb,${v >= 0 ? 'var(--s2)' : 'var(--neg)'} ${Math.round(Math.min(1, Math.abs(v) / 0.08) * 70)}%,transparent)`;
  const CATS = ['Standard', 'Cyclique'];

  // ================= MARCHÉ =================
  A.pages.marche = {
    render(main) {
      const S = A.ps.mk || (A.ps.mk = { bloc: '', cat: '', y0: A.Y0, y1: A.Y1, st: 'g', q: '', sort: 'a', dir: 1, page: 0 });
      const cats = Array.from(new Set(A.comp.map(c => c.cat))).sort();
      main.innerHTML = `
      <section class="sec"><div class="eyebrow">Explorer</div><h1>Le marché, ligne par ligne</h1>
        <p class="lede">Filtre l'ensemble des entreprises × années. Les graphiques et le tableau suivent les filtres, et r se règle en haut de la page.</p>
        <div class="bar-f">
          <label>Bloc<select id="fb"><option value="">Tous</option>${A.BLOCS.map(b => opt(b, A.blocLabel(b), S.bloc)).join('')}</select></label>
          <label>Catégorie<select id="fc"><option value="">Toutes</option>${cats.map(b => opt(b, b, S.cat)).join('')}</select></label>
          <label>De<select id="f0">${A.YEARS.map(y => opt(y, y, S.y0)).join('')}</select></label>
          <label>À<select id="f1">${A.YEARS.map(y => opt(y, y, S.y1)).join('')}</select></label>
          <label>Lignes<select id="fs">${opt('g', 'Avec un g implicite', S.st)}${opt('all', 'Toutes (avec ou sans g)', S.st)}${A.M.statuts_g.map(s => opt(s, 'Statut g : ' + s, S.st)).join('')}${opt('nocours', 'Sans cours (pas de g)', S.st)}</select></label>
          <label>Ticker<input type="search" id="fq" value="${esc(S.q)}" placeholder="ex. AAPL" style="width:110px"></label>
        </div></section>
      <section class="grid g4" id="mk-k"></section>
      <section class="grid g2">
        <div class="card"><h3>Répartition de g <span class="legend"><span><i class="sw bar" style="background:var(--s2)"></i>nombre de lignes</span></span></h3><div id="mk-h"></div></div>
        <div class="card"><h3>g médian par année <span class="legend"><span><i class="sw" style="background:var(--s2)"></i>médiane</span><span><i class="sw bar" style="background:var(--s2);opacity:.3"></i>moitié centrale</span></span></h3><div id="mk-l"></div></div>
      </section>
      <section class="sec"><h2>g médian par bloc et par année</h2><div class="tw" id="mk-hm"></div><p class="note">Valeurs en %, g médian. Cases vides : moins de 3 lignes. Couleur saturée à ±8 %. Plus la case est foncée, plus g s'éloigne de zéro (orange : positif, rouge : négatif).</p></section>
      <section class="sec"><h2>Les lignes <span class="note" id="mk-n"></span></h2><div class="pager"><button id="pp">←</button><span id="pg"></span><button id="pn">→</button><button id="dl" style="margin-left:auto">Exporter en CSV</button></div><div class="tw maxh" id="mk-t"></div></section>`;
      const filt = () => A.rows.filter(o => (!S.bloc || o.bloc === S.bloc) && (!S.cat || o.cat === S.cat) && o.a >= S.y0 && o.a <= S.y1 &&
        (S.st === 'all' ? true : S.st === 'g' ? o.g != null : S.st === 'nocours' ? o.sg == null : o.sgn === S.st) && (!S.q || o.t.toUpperCase().indexOf(S.q.toUpperCase()) === 0));
      const cols = [['t', 'Ticker', o => o.t, true], ['a', 'Année', o => o.a], ['bloc', 'Bloc', o => A.blocLabel(o.bloc), true], ['cat', 'Catégorie', o => o.cat, true], ['ve', 'VE (M$)', o => o.ve], ['fcfr', 'FCF retenu (M$)', o => o.fcfr], ['reff', 'r', o => o.reff], ['g', 'g implicite', o => o.g], ['gr', 'g réel 3 ans', o => o.gr], ['ecart', 'Écart (g réel − g)', o => o.ecart], ['x1', 'Excès de rendement, 1 an', o => o.x1], ['sgn', 'Statut g', o => o.sgn || o.spn.replace(/_/g, ' '), true]];
      const draw = () => {
        const L = filt(), G = L.filter(o => o.g != null).map(o => o.g), cos = new Set(L.map(o => o.cik));
        $('mk-k').innerHTML = [[nf(L.length, 0), 'lignes sélectionnées'], [nf(cos.size, 0), 'sociétés'], [G.length ? pc(A.median(G)) : '–', 'g implicite médian'], [G.length ? pc(A.quantile(G, .25)) + ' à ' + pc(A.quantile(G, .75)) : '–', 'moitié centrale de g (du 25e au 75e centile)']].map(k => `<div class="card kpi"><b>${k[0]}</b><span>${k[1]}</span></div>`).join('');
        const bins = []; for (let v = -0.10; v <= 0.1501; v += 0.01) bins.push(+v.toFixed(3));
        if (G.length) A.hist($('mk-h'), { values: G, bins, every: 5, fmt: v => nf(v * 100, 0) + ' %', median: A.median(G), h: 200, label: 'Répartition de g' }); else $('mk-h').innerHTML = '<div class="empty">Aucune ligne avec g.</div>';
        const by = A.groupBy(L.filter(o => o.g != null), o => o.a), ys = A.YEARS.filter(y => y >= S.y0 && y <= S.y1);
        const st = ys.map(y => { const a = (by.get(y) || []).map(o => o.g); return a.length >= 3 ? { m: A.median(a), lo: A.quantile(a, .25), hi: A.quantile(a, .75), n: a.length } : null; });
        A.lineChart($('mk-l'), { xs: ys, label: 'g médian par année', h: 200, zero: true, yfmt: t => pc(t, 0), series: [{ kind: 'band', color: 'var(--s2)', lo: st.map(s => s && s.lo), hi: st.map(s => s && s.hi) }, { kind: 'line', color: 'var(--s2)', v: st.map(s => s && s.m) }], tip: i => st[i] ? `<b>${ys[i]}</b><br>médiane ${pc(st[i].m)}<br>${pc(st[i].lo)} à ${pc(st[i].hi)}<br>${nf(st[i].n, 0)} lignes` : `<b>${ys[i]}</b><br>moins de 3 lignes` });
        const gb = A.groupBy(L.filter(o => o.g != null), o => o.bloc + '|' + o.a);
        $('mk-hm').innerHTML = `<table class="heat"><thead><tr><th class="l">Bloc</th>${ys.map(y => `<th>${String(y).slice(2)}</th>`).join('')}</tr></thead><tbody>${A.BLOCS.filter(b => !S.bloc || b === S.bloc).map(b => `<tr><td class="l">${esc(A.blocLabel(b))}</td>${ys.map(y => { const a = (gb.get(b + '|' + y) || []).map(o => o.g); const v = a.length >= 3 ? A.median(a) : null; return `<td style="${heatBg(v)}" title="${a.length} lignes">${v == null ? '' : nf(v * 100, 0)}</td>`; }).join('')}</tr>`).join('')}</tbody></table>`;
        const ci = cols.findIndex(c => c[0] === S.sort), get = cols[ci][2], txt = cols[ci][3];
        const sorted = L.slice().sort((x, y) => { const a = get(x), b = get(y); if (a == null && b == null) return 0; if (a == null) return 1; if (b == null) return -1; return (txt ? String(a).localeCompare(String(b), 'fr') : a - b) * S.dir; });
        const per = 50, np = Math.max(1, Math.ceil(sorted.length / per)); if (S.page >= np) S.page = np - 1;
        $('mk-n').textContent = '· ' + nf(sorted.length, 0);
        $('pg').textContent = 'Page ' + (S.page + 1) + ' sur ' + np;
        $('mk-t').innerHTML = `<table><thead><tr>${cols.map(c => `<th class="s${c[3] ? ' l' : ''}" data-k="${c[0]}" tabindex="0">${c[1]}${S.sort === c[0] ? (S.dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('')}</tr></thead><tbody>${sorted.slice(S.page * per, (S.page + 1) * per).map((o, i) => `<tr class="click" tabindex="0" data-i="${S.page * per + i}"><td class="l">${esc(o.t)}${o.dup ? ' <span class="pill bad">doublon</span>' : ''}</td><td>${o.a}</td><td class="l">${esc(A.blocLabel(o.bloc))}</td><td class="l">${o.cat}</td><td>${nf(o.ve, 0)}</td><td>${nf(o.fcfr, 0)}</td><td>${pc(o.reff)}</td><td>${sp(o.g)}</td><td>${sp(o.gr)}</td><td>${A.pts(o.ecart)}</td><td>${sp(o.x1, 0)}</td><td class="l">${o.sgn ? `<span class="pill ${o.sgn === 'ok' ? 'ok' : 'warn'}">${esc(o.sgn)}</span>` : `<span class="pill bad">${esc(o.spn.replace(/_/g, ' '))}</span>`}</td></tr>`).join('')}</tbody></table>`;
        $('mk-t').querySelectorAll('th.s').forEach(th => { const f = () => { if (S.sort === th.dataset.k) S.dir = -S.dir; else { S.sort = th.dataset.k; S.dir = 1; } S.page = 0; draw(); }; th.onclick = f; th.onkeydown = e => { if (e.key === 'Enter') f(); }; });
        $('mk-t').querySelectorAll('tr.click').forEach(tr => { tr.onclick = () => gotoCo(sorted[+tr.dataset.i]); tr.onkeydown = e => { if (e.key === 'Enter') gotoCo(sorted[+tr.dataset.i]); }; });
        if (!sorted.length) $('mk-t').innerHTML = '<div class="empty">Aucune ligne ne correspond aux filtres.</div>';
        $('dl').onclick = () => A.csv('reverse_dcf_lignes.csv', cols.map(c => c[1]).concat(['CIK']), sorted.map(o => cols.map(c => { const v = c[2](o); return typeof v === 'number' ? v : v; }).concat([o.cik])));
        $('pp').onclick = () => { if (S.page > 0) { S.page--; draw(); } }; $('pn').onclick = () => { if (S.page < np - 1) { S.page++; draw(); } };
      };
      const bind = (id, k, num) => $(id).addEventListener('change', e => { S[k] = num ? +e.target.value : e.target.value; if (S.y0 > S.y1) { if (k === 'y0') S.y1 = S.y0; else S.y0 = S.y1; $('f0').value = S.y0; $('f1').value = S.y1; } S.page = 0; draw(); });
      bind('fb', 'bloc'); bind('fc', 'cat'); bind('f0', 'y0', 1); bind('f1', 'y1', 1); bind('fs', 'st');
      $('fq').addEventListener('input', e => { S.q = e.target.value.trim(); S.page = 0; draw(); });
      draw();
    }
  };

  // ================= BLOCS =================
  A.pages.blocs = {
    render(main) {
      const S = A.ps.bl || (A.ps.bl = { sel: A.BLOCS[0] });
      const stats = {};
      for (const b of A.BLOCS) { const L = A.rows.filter(o => o.bloc === b); stats[b] = { L, A: A.testA(L), B: A.testB(L).quart, med: A.medBy(b), ng: L.filter(o => o.g != null).length, nc: new Set(L.filter(o => o.g != null).map(o => o.cik)).size }; }
      const all = A.medBy(null);
      main.innerHTML = `
      <section class="sec"><div class="eyebrow">Comparer</div><h1>Dix blocs sectoriels</h1>
        <p class="lede">Les sociétés sont regroupées par secteur (code SIC de la SEC, avec quelques corrections manuelles). Trait orange : g implicite médian du bloc. Pointillé gris : médiane de tout le marché. Sous chaque graphique, « trop prudent » = part des lignes où le FCF réel dépasse g, et ρ = lien entre le rang de g et le rang de la croissance réelle. Bloc Luxe : échantillon petit, à lire avec prudence.</p>
        <div class="grid g3" id="bl-cards">${A.BLOCS.map(b => { const s = stats[b], a = s.A; return `<div class="card mini" data-b="${esc(b)}" tabindex="0" role="button" style="${b === S.sel ? 'outline:2px solid var(--s2)' : ''}"><h3>${esc(A.blocLabel(b))}</h3>
          ${A.spark([{ v: A.YEARS.map(y => all.med[y]), color: 'var(--muted)', dash: true, w: 1.3 }, { v: A.YEARS.map(y => s.med.med[y]), color: 'var(--s2)' }], A.YEARS, 260, 54)}
          <div class="note">${nf(s.nc, 0)} sociétés · ${nf(s.ng, 0)} lignes avec g</div>
          <div class="note">g médian <b style="color:var(--ink)">${a.n ? pc(a.gMed) : '–'}</b> · FCF réel <b style="color:var(--ink)">${a.n ? pc(a.grMed) : '–'}</b></div>
          <div class="note">trop prudent ${a.n ? nf(a.prudent * 100, 0) + ' %' : '–'} · ρ ${a.n ? nf(a.rho, 2) : '–'}</div></div>`; }).join('')}</div></section>
      <section class="sec"><h2 id="bl-t"></h2><div class="grid g2"><div class="card"><h3>Test B dans ce bloc <span class="legend"><span>excès de rendement moyen par quartile de g</span></span></h3><div id="bl-b"></div></div><div class="card"><h3>g implicite médian par année <span class="legend"><span><i class="sw" style="background:var(--s2)"></i>bloc</span><span><i class="sw" style="background:var(--muted)"></i>marché</span></span></h3><div id="bl-l"></div></div></div>
        <div class="tw maxh" id="bl-tab"></div></section>`;
      const show = () => {
        const b = S.sel, s = stats[b];
        $('bl-t').textContent = A.blocLabel(b) + ' : les sociétés';
        const mx = Math.max(0.05, ...s.B.flatMap(q => [Math.abs(q.x1), Math.abs(q.x3)]));
        const rb = (l, v) => `<div class="row2"><span>${l}</span><i style="width:${Math.max(1, Math.abs(v) / mx * 100)}%;background:${v >= 0 ? 'var(--s1)' : 'var(--neg)'}"></i><em>${sp(v, 1)}</em></div>`;
        $('bl-b').innerHTML = s.B.some(q => q.n) ? s.B.map(q => `<div style="margin-bottom:6px"><b style="font-size:12.5px">Q${q.q + 1}${q.q === 0 ? ' · g le plus bas' : q.q === 3 ? ' · g le plus haut' : ''} · ${nf(q.n, 0)} lignes</b>${rb('1 an', q.x1)}${rb('3 ans par an', q.x3)}</div>`).join('') + '<p class="note">Les quartiles sont formés au sein du bloc et de l\'année (au moins 8 lignes).</p>' : '<div class="empty">Pas assez de lignes.</div>';
        A.lineChart($('bl-l'), { xs: A.YEARS, label: 'g médian du bloc', h: 190, zero: true, yfmt: t => pc(t, 0), series: [{ kind: 'dash', color: 'var(--muted)', v: A.YEARS.map(y => all.med[y]) }, { kind: 'band', color: 'var(--s2)', lo: A.YEARS.map(y => s.med.p25[y]), hi: A.YEARS.map(y => s.med.p75[y]) }, { kind: 'line', color: 'var(--s2)', v: A.YEARS.map(y => s.med.med[y]) }], tip: i => { const y = A.YEARS[i]; return `<b>${y}</b><br>bloc ${pc(s.med.med[y])}<br>marché ${pc(all.med[y])}<br>${nf(s.med.n[y], 0)} lignes`; } });
        const byc = A.groupBy(s.L.filter(o => o.g != null), o => o.t);
        const rows = Array.from(byc, ([t, L]) => { const gr = L.map(o => o.gr).filter(v => v != null); return { t, cat: L[0].cat, n: L.length, g: A.median(L.map(o => o.g)), gr: gr.length ? A.median(gr) : null, a0: L[0].a, a1: L[L.length - 1].a }; }).sort((x, y) => y.g - x.g);
        $('bl-tab').innerHTML = `<table><thead><tr><th>Société</th><th class="l">Cat.</th><th>Années avec g</th><th>De</th><th>À</th><th>g médian</th><th>FCF réel médian (3 ans)</th></tr></thead><tbody>${rows.map(r => `<tr><td>${A.link(r.t)}</td><td class="l">${r.cat}</td><td>${r.n}</td><td>${r.a0}</td><td>${r.a1}</td><td>${sp(r.g)}</td><td>${sp(r.gr)}</td></tr>`).join('')}</tbody></table>`;
      };
      show();
      main.querySelectorAll('.mini').forEach(c => { const f = () => { S.sel = c.dataset.b; A.pages.blocs.render(main); $('bl-t').scrollIntoView({ behavior: 'smooth', block: 'start' }); }; c.onclick = f; c.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); f(); } }; });
    }
  };

  // ================= BACKTEST =================
  A.pages.backtest = {
    render(main) {
      const S = A.ps.bt || (A.ps.bt = { bloc: '', h: 3 });
      S.univ = A.state.univ;
      const list = S.bloc ? A.rows.filter(o => o.bloc === S.bloc) : A.rows;
      const a = A.testA(list), bAll = A.testB(A.rows), bSel = S.bloc ? A.testB(list) : bAll;
      const [p1, ny1] = A.winCount(bAll, 's1'), [p3, ny3] = A.winCount(bAll, 's3');
      const univTxt = { membres: 'sociétés membres du S&amp;P 500 à la date de clôture', 'hors indice': 'sociétés hors indice à la date', tous: 'toutes les sociétés' }[S.univ];
      const kf = (b, t) => `<div class="card kpi"><b>${b}</b><span>${t}</span></div>`;
      const verdict = a.n ? `Sur ${nf(a.n, 0)} lignes (${univTxt})${S.bloc ? ' du bloc ' + esc(A.blocLabel(S.bloc)) : ''}, le FCFF a grandi de ${pc(a.grMed)} par an (médiane) alors que le prix en supposait ${pc(a.gMed)} : écart médian ${A.pts(a.ecMed)} (médiane des écarts ligne par ligne, pas la différence des deux médianes), FCF meilleur que ce que le prix supposait dans ${nf(a.prudent * 100, 0)} % des cas. Un g plus haut va de pair avec une croissance plus haute (ρ = ${nf(a.rho, 2)}). « Trop prudent » veut seulement dire g réel &gt; g pour le r choisi : ce n'est pas la preuve que le marché se trompait.` : 'Pas assez de lignes pour ce bloc.';
      main.innerHTML = `
      <section class="sec"><div class="eyebrow">Les conclusions</div><h1>Le marché avait-il raison ?</h1>
        <p class="lede">Test A : on compare la croissance du FCFF supposée par le prix (g implicite) à celle observée ensuite (de la base à N+3 ; base = N−1, ou moyenne N−5 à N−1 pour les cycliques). Test B : les actions au g faible (FCF/VE élevé) ont-elles rapporté plus que celles au g élevé ? Les conclusions portent sur l'univers choisi ; les membres de l'indice sont l'univers de référence.</p>
        <div class="bar-f"><label>Bloc (test A et barres par quartile)<select id="bb"><option value="">Tous</option>${A.BLOCS.map(b => opt(b, A.blocLabel(b), S.bloc)).join('')}</select></label>
        <label>Univers<select id="bu"><option value="membres"${S.univ === 'membres' ? ' selected' : ''}>Membres du S&amp;P 500 à la date</option><option value="hors indice"${S.univ === 'hors indice' ? ' selected' : ''}>Hors indice à la date</option><option value="tous"${S.univ === 'tous' ? ' selected' : ''}>Toutes les sociétés</option></select></label>
        <label>Horizon du test B<span class="seg2"><button id="h1y" aria-pressed="${S.h === 1}">1 an</button><button id="h3y" aria-pressed="${S.h === 3}">3 ans</button></span></label></div></section>
      <section class="sec"><h2>Test A : g implicite contre croissance réelle du FCF</h2>
        <div class="grid g4">${kf(nf(a.n || 0, 0), 'lignes testées')}${kf(a.n ? nf(a.rho, 2) : '–', 'corrélation de rang ρ (g, g réel)')}${kf(a.n ? nf(a.prudent * 100, 0) + ' %' : '–', 'marché trop prudent (g réel > g)')}${kf(a.n ? A.pts(a.ecMed) : '–', 'écart médian (g réel − g)')}</div>
        <p class="story">${verdict}</p>
        <div class="card"><h3>Un point = une entreprise et une année <span class="legend"><span><i class="sw dot" style="border-color:var(--s1)"></i>ligne (cercle vide : point hors du graphique, ramené au bord)</span><span><i class="sw dot" style="border-color:var(--s2);background:var(--s2)"></i>médiane de chaque dixième des lignes rangées par g</span><span><i class="sw" style="background:var(--ink2)"></i>diagonale : le prix voyait juste</span></span></h3><div id="bt-sc"></div><p class="note">Au-dessus de la diagonale, le FCF a fait mieux que ce que le prix supposait. Clique un point pour ouvrir l'entreprise.</p></div>
        <div class="card"><h3>Par bloc <span class="legend"><span><i class="sw dot" style="background:var(--s2);border-color:var(--s2)"></i>g implicite médian</span><span><i class="sw dot" style="background:var(--s3);border-color:var(--s3)"></i>croissance réelle médiane</span></span></h3><div class="dumb" id="bt-db"></div></div></section>
      <section class="sec"><h2>Test B : acheter les g bas ou les g hauts ?</h2>
        <div class="grid g2"><div class="card"><h3>Excès de rendement moyen par quartile de FCF/VE (Q1 = g le plus bas) <span class="legend"><span>${S.h === 1 ? '1 an' : '3 ans par an'}</span></span></h3><div id="bt-q"></div></div>
        <div class="card"><h3>Q1 − Q4 par année <span class="legend"><span><i class="sw bar" style="background:var(--s1)"></i>g bas a gagné</span><span>${S.h === 1 ? '1 an' : '3 ans par an'}</span></span></h3><div id="bt-y"></div><p class="note">Quartiles par année sur l'univers choisi (au moins 100 lignes par année). Ce graphique ne suit pas le filtre de bloc.</p></div></div>
        <p class="story">Les g bas ont battu les g hauts <b>${p1} années sur ${ny1}</b> à 1 an et <b>${p3} sur ${ny3}</b> à 3 ans (${univTxt} ; rendement total dividendes inclus, départ après le dépôt du 10-K, excès par rapport à la médiane de l'année dans cet univers). Ces décomptes ne sont pas des tests statistiques et ne disent pas qu'on peut acheter les g bas : les années se chevauchent et le résultat dépend de l'univers (changer d'univers pour le voir).</p></section>
      <section class="sec"><h2>Et si la prime de risque change ?</h2><div class="tw" id="bt-sens"></div><p class="note">Même calcul pour d'autres primes de risque (taux à 10 ans et structure de capital inchangés) et, en dernière ligne, pour l'ancien r fixe de 9 % (les cycliques gardent +1 point si la case est cochée). La ligne en gras est celle du curseur actuel. Ce tableau porte sur l'univers choisi plus haut. Leçon : ρ bouge à peine, mais le g médian et la part de « trop prudent » bougent beaucoup avec r. Le classement des sociétés est robuste, le niveau de g ne l'est pas.</p></section>`;
      // scatter
      const L = a.rows || [], pts = L.map(o => ({ x: o.g, y: o.gr, o }));
      if (pts.length) {
        const srt = L.slice().sort((x, y) => x.g - y.g), dec = [];
        for (let i = 0; i < 10; i++) { const c = srt.slice(Math.floor(i * srt.length / 10), Math.floor((i + 1) * srt.length / 10)); if (c.length) dec.push({ x: A.median(c.map(o => o.g)), y: A.median(c.map(o => o.gr)), lo: A.quantile(c.map(o => o.gr), .25), hi: A.quantile(c.map(o => o.gr), .75) }); }
        A.scatter($('bt-sc'), { pts, deciles: dec, xlo: -0.10, xhi: 0.12, ylo: -0.30, yhi: 0.50, xfmt: t => nf(t * 100, 0) + ' %', yfmt: t => nf(t * 100, 0) + ' %', xtitle: 'g implicite (ce que le prix supposait)', ytitle: 'croissance réelle du FCFF par an (base à N+3)', h: 400, label: 'g implicite contre croissance réelle du FCF',
          tip: p => `<b>${esc(p.o.t)} ${p.o.a}</b><br>g implicite ${sp(p.x)}<br>croissance réelle du FCF ${sp(p.y)}<br>${esc(A.blocLabel(p.o.bloc))}`, onPick: p => gotoCo(p.o) });
      } else $('bt-sc').innerHTML = '<div class="empty">Aucune ligne.</div>';
      // dumbbell
      const lines = A.BLOCS.map(b => ({ b, t: A.testA(A.rows.filter(o => o.bloc === b)) })).filter(x => x.t.n).sort((x, y) => y.t.ecMed - x.t.ecMed).map(x => ({ name: A.blocLabel(x.b), a: x.t.gMed, b: x.t.grMed, ec: x.t.ecMed, rho: x.t.rho, tip: `<b>${esc(A.blocLabel(x.b))}</b><br>g implicite ${pc(x.t.gMed)}<br>FCF réel ${pc(x.t.grMed)}<br>trop prudent ${nf(x.t.prudent * 100, 0)} % · ${nf(x.t.n, 0)} lignes` }));
      lines.unshift({ name: 'Tous les blocs', a: A.testA(A.rows).gMed, b: A.testA(A.rows).grMed, ec: A.testA(A.rows).ecMed, rho: A.testA(A.rows).rho, tip: 'Marché entier' });
      A.dumbbell($('bt-db'), lines);
      // quartiles
      const k = S.h === 1 ? 'x1' : 'x3', mx = Math.max(0.03, ...bSel.quart.map(q => Math.abs(q[k] || 0)));
      $('bt-q').innerHTML = bSel.quart.every(q => !q.n) ? '<div class="empty">Pas assez de lignes.</div>' : bSel.quart.map(q => `<div class="row2" style="margin-bottom:5px"><span>Q${q.q + 1}${q.q === 0 ? ' (g bas)' : q.q === 3 ? ' (g haut)' : ''}</span><i style="width:${Math.max(1, Math.abs(q[k]) / mx * 100)}%;background:${q[k] >= 0 ? 'var(--s1)' : 'var(--neg)'}"></i><em>${sp(q[k], 1)}</em></div>`).join('') + `<p class="note">${nf(A.sum(bSel.quart.map(q => q.n)), 0)} lignes · quartiles dans chaque bloc et chaque année (groupes de moins de 8 lignes écartés).</p>`;
      const sk = S.h === 1 ? 's1' : 's3', ys = bAll.years.filter(y => y[sk] != null), xs = ys.map(y => y.a);
      A.lineChart($('bt-y'), { xs, label: 'Q1 moins Q4 par année', h: 200, zero: true, yfmt: t => nf(t * 100, 0) + ' pts', series: [{ kind: 'bar', color: 'var(--s1)', v: ys.map(y => y[sk]) }], tip: i => { const y = ys[i]; return `<b>${y.a}</b> · ${nf(S.h === 1 ? y.n : y.n3, 0)} lignes<br>Q1 ${sp(S.h === 1 ? y.q1x1 : y.q1x3, 1)}<br>Q4 ${sp(S.h === 1 ? y.q4x1 : y.q4x3, 1)}<br>Q1 − Q4 ${sp(y[sk], 1)}`; } });
      // sensibilité à r
      const cyc = A.state.cyc, cur = A.state.prime, fixe = A.state.mode === 'fixe';
      const ps = [0.03, 0.04, 0.05, 0.06, 0.07, 0.08].concat(cur % 0.01 > 1e-9 && [0.03, 0.04, 0.05, 0.06, 0.07, 0.08].indexOf(+cur.toFixed(3)) < 0 ? [cur] : []).sort((x, y) => x - y);
      const calc = () => { const ta = A.testA(A.rows), tb = A.testB(A.rows); const w1 = A.winCount(tb, 's1'), w3 = A.winCount(tb, 's3'); return { ta, p1: w1[0], n1: w1[1], p3: w3[0], n3: w3[1], rm: A.state.rShow }; };
      const rowsS = ps.map(p => Object.assign(A.atPrime(p, cyc, calc), { lab: 'prime ' + pc(p), bold: !fixe && Math.abs(p - cur) < 1e-9 }));
      rowsS.push(Object.assign(A.atR(0.09, cyc, calc), { lab: 'r fixe 9 % (ancienne méthode)', bold: fixe }));
      $('bt-sens').innerHTML = `<table><thead><tr><th>Réglage</th><th>r médian</th><th>Lignes test A</th><th>g médian</th><th>FCF réel médian</th><th>Trop prudent</th><th>ρ</th><th>Q1 gagne (1 an)</th><th>Q1 gagne (3 ans)</th></tr></thead><tbody>${rowsS.map(x => `<tr style="${x.bold ? 'font-weight:800' : ''}"><td class="l">${x.lab}</td><td>${pc(x.rm)}</td><td>${nf(x.ta.n, 0)}</td><td>${pc(x.ta.gMed)}</td><td>${pc(x.ta.grMed)}</td><td>${nf(x.ta.prudent * 100, 0)} %</td><td>${nf(x.ta.rho, 2)}</td><td>${x.p1} / ${x.n1}</td><td>${x.p3} / ${x.n3}</td></tr>`).join('')}</tbody></table>`;
      $('bb').onchange = e => { S.bloc = e.target.value; A.pages.backtest.render(main); };
      $('bu').onchange = e => { A.state.univ = e.target.value; A.pages.backtest.render(main); };
      $('h1y').onclick = () => { S.h = 1; A.pages.backtest.render(main); };
      $('h3y').onclick = () => { S.h = 3; A.pages.backtest.render(main); };
    }
  };
})();
