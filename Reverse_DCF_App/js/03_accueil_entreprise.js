/* 03 : page Accueil et page Entreprise */
(function () {
  const A = window.A, $ = A.$, esc = A.esc, nf = A.nf, pc = A.pc, sp = A.sp, fM = A.fM, usd = A.usd;
  A.ps = {};

  // médiane de g par bloc et année (au r courant), avec cache
  const rec0 = A.recompute;
  A.recompute = function () { rec0(); A.medCache = {}; };
  A.medBy = function (bloc) {
    const key = bloc || '*';
    if (A.medCache[key]) return A.medCache[key];
    const m = {}, q = {};
    for (const o of A.rows) { if (o.g == null || (bloc && o.bloc !== bloc)) continue; (m[o.a] = m[o.a] || []).push(o.g); }
    const med = {}, p25 = {}, p75 = {}, n = {};
    A.YEARS.forEach(y => { const a = m[y]; med[y] = a && a.length >= 3 ? A.median(a) : null; p25[y] = a && a.length >= 3 ? A.quantile(a, 0.25) : null; p75[y] = a && a.length >= 3 ? A.quantile(a, 0.75) : null; n[y] = a ? a.length : 0; });
    return (A.medCache[key] = { med, p25, p75, n });
  };
  A.medCache = {};

  const kpi = (b, t) => `<div class="card kpi"><b>${b}</b><span>${t}</span></div>`;

  // ---------- résumé "ce que disent les tests", au r courant ----------
  A.summaryTests = function (list) {
    const a = A.testA(list), b = A.testB(list);
    const [p1, ny] = A.winCount(b, 's1'), [p3, ny3] = A.winCount(b, 's3');
    return { a, b, p1, p3, ny, ny3 };
  };

  A.pages.accueil = {
    render(main) {
      const P = A.M.pipeline, st = A.state, withG = A.rows.filter(o => o.g != null), cos = new Set(withG.map(o => o.cik));
      const S = A.summaryTests(A.rows), a = S.a;
      const funnel = [
        ['Lignes de fondamentaux (SEC, ' + nf(P.fondamentaux_cik, 0) + ' sociétés)', P.fondamentaux_lignes],
        ['Lignes pour lesquelles on a cherché un cours', P.prix_lignes],
        ['Lignes avec cours et capitalisation', P.prix_statuts.ok],
        ['Lignes avec g implicite calculé', P.g_statuts.ok],
        ['Lignes du test A (FCF réel connu à N+4)', P.test_a],
        ['Lignes du test B à 3 ans (cours connu à départ + 3 ans)', P.test_b_3ans]
      ];
      const mx = funnel[0][1];
      const med = A.medBy(null);
      main.innerHTML = `
      <section class="sec">
        <div class="eyebrow">Projet Reverse DCF · données SEC et cours de marché · ${A.Y0}–${A.Y1}</div>
        <h1>Quelle croissance le prix d'une action suppose-t-il ?</h1>
        <p class="lede">Pour chaque entreprise du S&amp;P 500 et chaque année, on part du prix de marché et du cash dégagé (FCF), et on cherche la croissance éternelle <b>g</b> qui justifie ce prix. Puis on compare ce g à la croissance du FCF constatée ensuite.</p>
      </section>
      <section class="grid g4">
        ${kpi(nf(withG.length, 0), 'lignes avec un g implicite (entreprise × année)')}
        ${kpi(nf(cos.size, 0), 'sociétés (CIK) avec au moins un g')}
        ${kpi(A.Y0 + '–' + A.Y1, 'années de clôture d\'exercice')}
        ${kpi(A.BLOCS.length, 'blocs sectoriels')}
      </section>
      <section class="sec">
        <h2>Ce que disent les tests, avec ${A.rTxt()}</h2>
        <p class="story"><b>Test A, le FCF.</b> Sur ${nf(a.n, 0)} lignes, le g implicite médian est de <b>${pc(a.gMed)}</b> et la croissance réelle du FCFF entre la base (N−1, ou moyenne N−5 à N−1 pour les cycliques) et N+3 (par an) de <b>${pc(a.grMed)}</b> : le FCF a fait mieux que ce que le prix supposait (g réel &gt; g) dans <b>${nf(a.prudent * 100, 0)} %</b> des cas. Un g plus haut va de pair avec une croissance plus haute, lien réel mais modéré (corrélation de rang ρ = <b>${nf(a.rho, 2)}</b>, loin de 1).<br>
        <b>Test B, l'argent gagné.</b> Les actions au g le plus bas (Q1) ont, en moyenne, rapporté plus que celles au g le plus haut (Q4) ${S.p1} années sur ${S.ny} à 1 an, et ${S.p3} sur ${S.ny3} à 3 ans (excès de rendement total, dividendes inclus). Les quartiles sont formés sur FCF / VE ; les chiffres portent sur ${A.state.univ === 'tous' ? 'toutes les sociétés' : A.state.univ === 'membres' ? 'les sociétés membres du S&amp;P 500 à la date de clôture' : 'les sociétés hors indice à la date'} (choix modifiable sur la page Backtest).<br>
        <b>Lecture.</b> Le g implicite contient de l'information sur la croissance future, mais il ne suffit pas pour choisir des actions. Change r en haut de la page : les chiffres se recalculent.</p>
        <div class="grid g3">
          <a class="card" href="#/backtest" style="text-decoration:none;color:inherit"><h3>Backtest <span class="note">→</span></h3><p class="note">Nuage g contre croissance réelle du FCF, déciles, quartiles, par année et par bloc.</p></a>
          <a class="card" href="#/entreprise/AAPL" style="text-decoration:none;color:inherit"><h3>Une entreprise <span class="note">→</span></h3><p class="note">Le calcul de g étape par étape pour n'importe quelle société et n'importe quelle année.</p></a>
          <a class="card" href="#/qualite" style="text-decoration:none;color:inherit"><h3>Qualité des données <span class="note">→</span></h3><p class="note">Statuts, doublons, lignes à revoir, corrections manuelles, contrôle contre a14.</p></a>
        </div>
      </section>
      <section class="sec">
        <h2>D'où viennent les lignes</h2>
        <div class="card">${funnel.map(f => `<div class="fun"><span>${f[0]}</span><i style="width:${Math.max(2, f[1] / mx * 100)}%"></i><em>${nf(f[1], 0)}</em></div>`).join('')}</div>
        <p class="note">Les sociétés disparues du S&amp;P 500 n'ont souvent pas de cours : c'est le biais du survivant (voir la page Qualité).</p>
      </section>
      <section class="grid g2">
        <div class="card"><h3>g implicite médian par année <span class="legend"><span><i class="sw" style="background:var(--s2)"></i>médiane</span><span><i class="sw bar" style="background:var(--s2);opacity:.3"></i>moitié centrale des sociétés</span></span></h3><div id="h1"></div></div>
        <div class="card"><h3>Combien de lignes ont un g, par année <span class="legend"><span><i class="sw bar" style="background:var(--s1)"></i>lignes avec g</span></span></h3><div id="h2"></div></div>
      </section>`;
      A.lineChart($('h1'), { xs: A.YEARS, label: 'g implicite médian par année', h: 220, zero: true, yfmt: t => pc(t, 0),
        series: [{ kind: 'band', color: 'var(--s2)', lo: A.YEARS.map(y => med.p25[y]), hi: A.YEARS.map(y => med.p75[y]) }, { kind: 'line', color: 'var(--s2)', v: A.YEARS.map(y => med.med[y]) }],
        tip: i => { const y = A.YEARS[i]; return `<b>${y}</b><br>médiane : ${pc(med.med[y])}<br>moitié centrale : ${pc(med.p25[y])} à ${pc(med.p75[y])}<br>${nf(med.n[y], 0)} lignes`; } });
      A.lineChart($('h2'), { xs: A.YEARS, label: 'Nombre de lignes avec g par année', h: 220, zero: true, yfmt: t => nf(t, 0),
        series: [{ kind: 'bar', color: 'var(--s1)', v: A.YEARS.map(y => med.n[y]) }], tip: i => `<b>${A.YEARS[i]}</b><br>${nf(med.n[A.YEARS[i]], 0)} lignes avec g` });
    }
  };

  // ============ page Entreprise ============
  const tickersSorted = () => A.comp.map(c => c.t).sort((a, b) => a.localeCompare(b));

  function stepsHTML(w, co) {
    if (w.cap == null || w.ve == null) {
      return `<div class="card story">Pas de calcul pour ${w.a} : ${esc(w.spn.replace(/_/g, ' '))}${w.vf ? ' (' + esc(w.vf) + ')' : ''}. ${w.spn === 'ticker_introuvable' ? 'Ni Yahoo ni Tiingo ne donnent de cours pour ce titre, souvent parce que la société a disparu du marché.' : w.spn === 'avant_debut_historique' ? 'Le premier cours disponible est postérieur à la date de clôture.' : ''}</div>`;
    }
    const r = w.reff, g = w.g, mx = Math.max(w.cap, w.cap + w.dt, w.ve), cyc = w.cat === 'Cyclique';
    let fcfNote = '';
    if (cyc) {
      const ys = []; for (let y = w.a - 4; y <= w.a; y++) { const x = co.rows.find(q => q.a === y); if (x && x.fcf != null) ys.push(fM(x.fcf)); }
      fcfNote = `<div class="hint note">Cyclique : moyenne des FCFF de ${w.a - 4} à ${w.a} (${ys.join(' ; ')}).</div>`;
    }
    const fcfBig = w.fcfr != null ? `${fM(w.fcfr)}` : 'indisponible';
    let step4;
    if (g != null) step4 = `<div class="eq">g = (VE × r − FCF) / (VE + FCF)<br>g = (${A.fMd(w.ve)} × ${nf(r * 100, 1)} % − ${A.fMd(w.fcfr)}) / (${A.fMd(w.ve)} + ${A.fMd(w.fcfr)})</div><div class="big">${sp(g)}<small>par an, pour toujours</small></div>`;
    else step4 = `<div class="eq">Pas de g : ${esc(w.sgn || 'ligne absente de g_implicite.csv')}.</div><div class="note">${w.sgn === 'fcf trop faible' ? `FCF retenu / VE = ${pc(w.fcfr != null ? w.fcfr / w.ve : null, 2)}, sous le seuil de ${pc(A.M.params.FCF_MIN_RELATIF, 0)} : si le FCF est si petit, g serait presque égal à r quel que soit le prix et ne dirait rien.` : w.sgn === 'exclu' ? 'Exclusion manuelle de a12 (valeur aberrante).' : ''}</div>`;
    const yld = w.fcfr != null ? w.fcfr / w.ve : null;
    let proof = '';
    if (g != null) {
      const chk = w.fcfr * (1 + g) / (r - g);
      proof = `<div class="grid g2"><div class="card"><h3>Vérification</h3><p class="note">Si le FCF croît de ${pc(g)} par an à partir de ${fM(w.fcfr)} et qu'on exige ${pc(r)}, la valeur actuelle de tous les flux est :</p><div class="eq">${A.fMd(w.fcfr)} × (1 + ${nf(g, 4)}) / (${nf(r, 3)} − ${nf(g, 4)}) = <b>${A.fMd(chk)} Md$</b></div><p class="note">C'est la VE de l'étape 2 (${A.fMd(w.ve)} Md$).</p></div>
      <div class="card"><h3>L'intuition</h3><p class="note">Chaque dollar de VE rapporte ${pc(yld)} de FCF aujourd'hui. L'écart avec r doit venir de la croissance : g = (r − rendement) / (1 + rendement).</p><div class="eq">g = (${pc(r)} − ${pc(yld)}) / (1 + ${pc(yld)}) = <b>${sp(g)}</b></div></div></div>`;
    }
    return `<div class="steps">
      <div class="step"><span class="n">ÉTAPE 1</span><h3>Le cours, multiplié par le nombre d'actions</h3><div class="eq">${usd(w.px)} × ${nf(w.sh, 1)} M actions</div><div class="big">${A.fMd(w.cap)}<small>Md$ de capitalisation</small></div><div class="note">Cours coté le ${A.dateFr(w.dc)}, non ajusté des splits (divisions d'actions)${w.pxa != null && Math.abs(w.pxa - w.px) > 0.005 ? ' : ajusté, il vaudrait ' + usd(w.pxa) : ''}. Md$ = milliards de dollars.</div></div>
      <div class="step"><span class="n">ÉTAPE 2</span><h3>On ajoute la dette, on retire la trésorerie</h3><div class="eq">${A.fMd(w.cap)} <b>+</b> ${A.fMd(w.dt)} <b>−</b> ${A.fMd(w.cs)}</div><div class="big">${A.fMd(w.ve)}<small>Md$ de VE</small></div><div class="bars">${bar2('capitalisation', w.cap, mx, 'var(--s1)')}${bar2('+ dette', w.dt, mx, 'var(--s1l)')}${bar2('− trésorerie', w.cs, mx, 'var(--neutral)')}${bar2('= VE', w.ve, mx, 'var(--s1)')}</div></div>
      <div class="step"><span class="n">ÉTAPE 3</span><h3>Le cash réellement dégagé</h3><div class="eq">${w.ocf != null ? A.fMd(w.ocf) + ' <b>+</b> ' + A.fMd(w.ia || 0) + ' <b>−</b> ' + A.fMd(w.cpx) : 'OCF ou capex absent'}</div><div class="note">OCF + intérêts après impôt − capex : le flux disponible avant paiement des intérêts (FCFF), cohérent avec un WACC.</div><div class="big">${cyc ? A.fMd(w.fcfr) : A.fMd(w.fcf)}<small>Md$ de FCFF${cyc ? ' retenu' : ''}</small></div>${fcfNote}${w.ocf != null ? `<div class="bars">${bar2('OCF', w.ocf, Math.max(w.ocf, 1e-9), 'var(--s3)')}${bar2('+ intérêts après impôt', w.ia || 0, Math.max(w.ocf, 1e-9), 'var(--s3)')}${bar2('− capex', w.cpx, Math.max(w.ocf, 1e-9), 'var(--neutral)')}${bar2('= FCFF', Math.max(0, w.fcf), Math.max(w.ocf, 1e-9), 'var(--s3)')}</div>` : ''}</div>
      <div class="step g"><span class="n">ÉTAPE 4</span><h3>La croissance que ce prix suppose</h3>${step4}</div></div>${proof}`;
  }
  const bar2 = (l, v, mx, c) => `<div class="bar"><span>${l}</span><i style="width:${Math.max(1, Math.abs(v) / mx * 100)}%;background:${c}"></i></div>`;
  const rowBar = (l, v, mx, c, t) => `<div class="row2"><span>${l}</span><i style="width:${Math.max(1, Math.min(100, Math.abs(v) / mx * 100))}%;background:${c}"></i><em>${t}</em></div>`;

  function testsHTML(w) {
    let a, b;
    if (w.g == null) return `<div class="card story">Pas de test pour ${w.a} : il n'y a pas de g calculé pour cette ligne.</div>`;
    if (w.gr == null) a = `<div class="tag note">TEST A · LE FCF</div><p>Pas de test pour ${w.a} : il faut un FCFF positif ${w.cat === 'Cyclique' ? 'en moyenne de ' + (w.a - 5) + ' à ' + (w.a - 1) : 'en ' + (w.a - 1)} et en moyenne de ${w.a + 2} à ${w.a + 4}, et ils ne sont pas tous disponibles.</p>`;
    else {
      const e = w.gr - w.g, mx = Math.max(w.fa, w.fp), cls = e > 0.01 ? 'up' : e < -0.01 ? 'down' : '', txt = e > 0.01 ? 'le FCF a fait mieux que ce que le prix supposait' : e < -0.01 ? 'le FCF a fait moins bien que ce que le prix supposait' : 'le FCF a fait à peu près ce que le prix supposait';
      a = `<div class="tag note">TEST A · LE FCF</div>${rowBar(w.cat === 'Cyclique' ? 'FCFF moyen ' + (w.a - 5) + '–' + (w.a - 1) : 'FCFF de ' + (w.a - 1), w.fa, mx, 'var(--s3)', fM(w.fa))}${rowBar('FCFF moyen ' + (w.a + 2) + '–' + (w.a + 4), w.fp, mx, 'var(--s3)', fM(w.fp))}<p>Le FCFF passe de ${fM(w.fa)} ${w.cat === 'Cyclique' ? '(moyenne N−5 à N−1)' : '(N−1)'} à ${fM(w.fp)} (moyenne N+2 à N+4) : <b>${sp(w.gr)}</b> par an sur ${w.cat === 'Cyclique' ? '6 ans (du centre N−3 de la base au centre N+3)' : '4 ans (de N−1 au centre de la fenêtre, N+3)'}. Le prix de ${w.a} supposait ${sp(w.g)}. Écart de ${nf(Math.abs(e) * 100, 1)} points de pourcentage : <span class="chip ${cls}">${txt}</span></p>`;
    }
    if (w.r1 == null) b = `<div class="tag note">TEST B · L'ARGENT GAGNÉ</div><p>Pas de test pour ${w.a} : le cours de départ (après le dépôt du 10-K) ou celui à 1 an manque.</p>`;
    else {
      const m1 = w.r1 - w.x1, has3 = w.r3 != null && w.x3 != null, m3 = has3 ? w.r3 - w.x3 : null;
      const mx = Math.max(Math.abs(w.r1), Math.abs(m1), has3 ? Math.abs(w.r3) : 0, has3 ? Math.abs(m3) : 0, 0.05), col = v => (v >= 0 ? 'var(--s1)' : 'var(--neg)');
      b = `<div class="tag note">TEST B · L'ARGENT GAGNÉ (RENDEMENT TOTAL, DIVIDENDES INCLUS)</div>${rowBar('Société, 1 an', w.r1, mx, col(w.r1), sp(w.r1, 0))}${rowBar('Société médiane, 1 an', m1, mx, 'var(--neutral)', sp(m1, 0))}${has3 ? rowBar('Société, 3 ans (par an)', w.r3, mx, col(w.r3), sp(w.r3, 0)) + rowBar('Société médiane, 3 ans (par an)', m3, mx, 'var(--neutral)', sp(m3, 0)) : ''}<p>Acheter après le dépôt du 10-K de ${w.a} rapportait <b>${sp(w.r1, 0)}</b> la première année, ${w.x1 >= 0 ? nf(w.x1 * 100, 0) + ' points de plus' : nf(-w.x1 * 100, 0) + ' points de moins'} que la société médiane de l'échantillon cette année-là.${has3 ? ` Sur 3 ans : ${sp(w.r3, 0)} par an (${w.x3 >= 0 ? '+' : '−'}${nf(Math.abs(w.x3) * 100, 0)} points par an contre la société médiane). Le départ est le premier jour de bourse après le dépôt du 10-K, quand les comptes sont publics (clôture + 90 jours si la date de dépôt est inconnue).` : ''} Ce test ne regarde pas le FCF.</p>`;
    }
    return `<div class="grid g2"><div class="card">${a}</div><div class="card">${b}</div></div>`;
  }

  A.pages.entreprise = {
    render(main, arg) {
      const co = A.byTicker[arg];
      if (!co) {
        const t0 = A.byTicker['AAPL'] ? 'AAPL' : A.comp[0].t;
        if (arg) { main.innerHTML = `<section class="sec"><h1>Société introuvable</h1><p>« ${esc(arg)} » n'est pas dans les données. <a href="#/entreprise/${t0}">Voir ${t0}</a>.</p></section>`; return; }
        location.replace('#/entreprise/' + t0); return;
      }
      const rows = co.rows, ps = A.ps.ent || (A.ps.ent = {});
      const yearsOk = rows.map(r => r.a);
      if (!yearsOk.includes(ps.year)) { ps.t = co.t; const last = rows.filter(r => r.g != null).pop() || rows[rows.length - 1]; ps.year = last.a; }
      const w = rows.find(r => r.a === ps.year);
      const list = tickersSorted(), pos = list.indexOf(co.t);
      const gs = rows.filter(r => r.g != null), grs = rows.map(r => r.gr).filter(v => v != null);
      const bm = A.medBy(co.bloc);
      main.innerHTML = `
      <section class="sec">
        <div class="bar-f">
          <label>Société (ticker)<input type="text" id="tk" list="tkl" value="${esc(co.t)}" autocomplete="off" style="width:150px"></label>
          <datalist id="tkl">${A.comp.map(c => `<option value="${esc(c.t)}">${esc(A.blocLabel(c.bloc))}</option>`).join('')}</datalist>
          <div class="seg2"><button id="pv" aria-label="Société précédente">←</button><button id="nx" aria-label="Société suivante">→</button></div>
          <label style="flex:1 1 280px">Année de clôture : <b id="yo" style="color:var(--ink)">${ps.year}</b><input type="range" id="yy" min="${rows[0].a}" max="${rows[rows.length - 1].a}" step="1" value="${ps.year}"></label>
        </div>
        <h1>${esc(co.t)}</h1>
        <p class="lede">${esc(co.sicd || 'SIC inconnu')} · bloc <b>${esc(A.blocLabel(co.bloc))}</b> · catégorie <b>${esc(co.cat)}</b> · CIK ${esc(co.cik)}${co.src && co.src.indexOf('manuel') >= 0 ? ' · bloc corrigé à la main' : ''}</p>
        <div class="grid g4">
          <div class="card kpi"><b>${rows.length}</b><span>années dans les données (${rows[0].a}–${rows[rows.length - 1].a})</span></div>
          <div class="card kpi"><b>${gs.length}</b><span>années avec un g implicite</span></div>
          <div class="card kpi"><b>${gs.length ? pc(A.median(gs.map(r => r.g))) : '–'}</b><span>g implicite médian (${A.rTxt()}, cycliques +1 pt si coché)</span></div>
          <div class="card kpi"><b>${grs.length ? pc(A.median(grs)) : '–'}</b><span>croissance réelle du FCFF médiane (base à N+3)</span></div>
        </div>
      </section>
      <section class="sec"><h2>Le calcul pour ${ps.year}</h2><div id="mach">${stepsHTML(w, co)}</div></section>
      <section class="sec"><h2>Année par année</h2>
        <div class="grid g2">
          <div class="card"><h3>Valeur d'entreprise <span class="legend"><span><i class="sw" style="background:var(--s1)"></i>VE, Md$</span></span></h3><div id="e1"></div></div>
          <div class="card"><h3>FCF <span class="legend"><span><i class="sw bar" style="background:var(--s3)"></i>OCF + intérêts après impôt − capex</span>${co.cat === 'Cyclique' ? '<span><i class="sw" style="background:var(--ink)"></i>FCF retenu (moyenne 5 ans)</span>' : ''}</span></h3><div id="e2"></div></div>
        </div>
        <div class="card"><h3>Ce que le marché supposait, ce qui s'est passé <span class="legend"><span><i class="sw" style="background:var(--s2)"></i>g implicite</span><span><i class="sw" style="background:var(--muted)"></i>médiane du bloc ${esc(A.blocLabel(co.bloc))}</span><span><i class="sw dot" style="border-color:var(--s3)"></i>croissance réelle du FCF sur 3 ans</span></span></h3><div id="e3"></div></div>
        <div class="card"><h3>Cours de clôture <span class="legend"><span><i class="sw" style="background:var(--s1)"></i>ajusté des splits, en $</span></span></h3><div id="e4"></div></div>
        <p class="note">Survole pour lire les valeurs, clique sur un graphique pour changer l'année.</p>
      </section>
      <section class="sec"><h2>Et après ? Que s'est-il passé ensuite pour un achat fin ${ps.year} ?</h2><div id="tst">${testsHTML(w)}</div></section>
      <section class="sec"><h2>Comparée aux autres sociétés du bloc en ${ps.year}</h2><div class="card"><div id="e5"></div></div></section>
      <section class="sec"><h2>Toutes les années</h2>
        <div class="tw maxh"><table><thead><tr><th>Année</th><th>Clôture</th><th>Prix</th><th>Actions (M)</th><th>Capitalisation</th><th>Dette</th><th>Cash</th><th>VE</th><th>OCF</th><th>Capex</th><th>FCF retenu</th><th>g</th><th>Statut g</th><th>Croissance réelle du FCF (3 ans)</th><th>Rendement du cours, 1 an</th><th class="l">Statut prix</th></tr></thead><tbody>
        ${rows.map(r => `<tr class="click ${r.a === ps.year ? 'sel' : ''}" tabindex="0" data-y="${r.a}"><td>${r.a}</td><td>${A.dateFr(r.dc)}</td><td>${usd(r.px)}</td><td>${nf(r.sh, 1)}</td><td>${fM(r.cap)}</td><td>${fM(r.dt)}</td><td>${fM(r.cs)}</td><td>${fM(r.ve)}</td><td>${fM(r.ocf)}</td><td>${fM(r.cpx)}</td><td>${fM(r.fcfr)}</td><td>${sp(r.g)}</td><td>${r.sgn ? `<span class="pill ${r.sgn === 'ok' ? 'ok' : 'warn'}">${esc(r.sgn)}</span>` : '–'}${r.dup ? ' <span class="pill bad" title="Une autre CIK de la même société a une ligne la même année">doublon</span>' : ''}</td><td>${sp(r.gr)}</td><td>${sp(r.r1, 0)}</td><td class="l"><span class="pill ${r.spn === 'ok' ? 'ok' : 'bad'}">${esc(r.spn.replace(/_/g, ' '))}</span></td></tr>`).join('')}
        </tbody></table></div>
      </section>`;
      const yrs = rows.map(r => r.a);
      const setY = y => { if (yrs.includes(y)) { ps.year = y; A.pages.entreprise.render(main, arg); } };
      const draw = () => {
        A.lineChart($('e1'), { xs: yrs, sel: ps.year, onSel: setY, label: 'VE', h: 160, ml: 48, yfmt: t => nf(t / 1000, 0), series: [{ kind: 'line', color: 'var(--s1)', v: rows.map(r => r.ve), label: v => A.fMd(v) }], tip: i => `<b>${yrs[i]}</b><br>VE : ${fM(rows[i].ve)}<br>Capitalisation : ${fM(rows[i].cap)}<br>Dette : ${fM(rows[i].dt)} · Cash : ${fM(rows[i].cs)}` });
        const sf = [{ kind: 'bar', color: 'var(--s3)', v: rows.map(r => r.fcf), label: v => A.fMd(v) }];
        if (co.cat === 'Cyclique') sf.push({ kind: 'line', color: 'var(--ink)', v: rows.map(r => r.fcfr), label: null });
        A.lineChart($('e2'), { xs: yrs, sel: ps.year, onSel: setY, label: 'FCF', h: 160, ml: 48, zero: true, yfmt: t => nf(t / 1000, 0), series: sf, tip: i => `<b>${yrs[i]}</b><br>FCF : ${fM(rows[i].fcf)}<br>OCF ${fM(rows[i].ocf)} − capex ${fM(rows[i].cpx)}${co.cat === 'Cyclique' ? '<br>FCF retenu : ' + fM(rows[i].fcfr) : ''}` });
        A.lineChart($('e3'), { xs: yrs, sel: ps.year, onSel: setY, label: 'g implicite et croissance réelle', h: 210, zero: true, yfmt: t => pc(t, 0),
          series: [{ kind: 'dash', color: 'var(--muted)', v: yrs.map(y => bm.med[y]) }, { kind: 'ring', color: 'var(--s3)', v: rows.map(r => r.gr) }, { kind: 'line', color: 'var(--s2)', v: rows.map(r => r.g), label: v => sp(v) }],
          tip: i => { const r = rows[i]; return `<b>${yrs[i]}</b><br>g implicite : ${sp(r.g)}<br>Médiane du bloc : ${sp(bm.med[yrs[i]])}<br>Croissance réelle du FCFF (base à N+3) : ${r.gr == null ? 'pas de test' : sp(r.gr)}`; } });
        A.lineChart($('e4'), { xs: yrs, sel: ps.year, onSel: setY, label: 'Cours', h: 150, ml: 48, yfmt: t => nf(t, 0), series: [{ kind: 'line', color: 'var(--s1)', v: rows.map(r => r.pxa), label: v => usd(v, 0) }], tip: i => `<b>${yrs[i]}</b><br>Cours ajusté : ${usd(rows[i].pxa)}<br>Cours de l'époque : ${usd(rows[i].px)}` });
        const peers = A.rows.filter(o => o.g != null && o.bloc === co.bloc && o.a === ps.year);
        A.strip($('e5'), { values: peers.map(o => o.g), mine: w.g, name: co.t, label: 'g des sociétés du bloc' });
        if (w.g == null) $('e5').innerHTML = '<div class="empty">Pas de g pour cette année : pas de comparaison.</div>';
        else { const lower = peers.filter(o => o.g < w.g).length; $('e5').insertAdjacentHTML('beforeend', `<p class="note">${esc(co.t)} a un g plus haut que ${nf(lower / Math.max(1, peers.length) * 100, 0)} % des ${peers.length} sociétés du bloc ${esc(A.blocLabel(co.bloc))} en ${ps.year}.</p>`); }
      };
      draw();
      $('yy').addEventListener('input', e => { setY(+e.target.value); });
      $('tk').addEventListener('change', e => { const v = e.target.value.trim().toUpperCase(); const c = A.comp.find(c => c.t.toUpperCase() === v) || A.comp.find(c => c.t.toUpperCase().indexOf(v) === 0); if (v && c) location.hash = '#/entreprise/' + encodeURIComponent(c.t); else { e.target.value = co.t; e.target.style.borderColor = 'var(--neg)'; e.target.title = 'Ticker introuvable'; setTimeout(() => (e.target.style.borderColor = ''), 1500); } });
      $('pv').onclick = () => { location.hash = '#/entreprise/' + encodeURIComponent(list[(pos - 1 + list.length) % list.length]); };
      $('nx').onclick = () => { location.hash = '#/entreprise/' + encodeURIComponent(list[(pos + 1) % list.length]); };
      main.querySelectorAll('tr.click').forEach(tr => { const f = () => setY(+tr.dataset.y); tr.addEventListener('click', f); tr.addEventListener('keydown', e => { if (e.key === 'Enter') f(); }); });
    }
  };
})();
