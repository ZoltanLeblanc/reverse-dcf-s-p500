/* 05 : pages Qualité et Méthode */
(function () {
  const A = window.A, $ = A.$, esc = A.esc, nf = A.nf, pc = A.pc, sp = A.sp, fM = A.fM;
  const P = A.M.pipeline;
  const tbl = (head, rows, cls) => `<div class="tw ${cls || ''}"><table><thead><tr>${head.map((h, i) => `<th class="${i === 0 ? '' : ''}">${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;

  // contrôle contre les sorties de a14 (WACC, prime 5 %, cycliques +1 pt), pour les trois univers
  function selfCheck(ref, run) {
    const out = { lines: [], ok: 0, tot: 0, maxd: 0 };
    const cmp = (name, mine, theirs) => {
      out.tot++;
      const d = mine == null || theirs == null || isNaN(theirs) ? (mine == null && (theirs == null || isNaN(theirs)) ? 0 : Infinity) : Math.abs(mine - theirs);
      if (d < 1e-4) out.ok++; else out.lines.push(`${name} : app ${mine} / a14 ${theirs}`);
      if (isFinite(d)) out.maxd = Math.max(out.maxd, d);
    };
    run(() => {
      const U = ['tous', 'membres', 'hors indice'], rA = {};
      ref.A.forEach(r => (rA[r[0] + '|' + r[1]] = r));
      const chk = (u, lab, list) => { const t = A.testA(list, u), r = rA[u + '|' + lab], nm = u + ' ' + lab; if (!r) { out.tot++; out.lines.push('absent de a14 : ' + nm); return; } cmp(nm + ' n', t.n, +r[2]); cmp(nm + ' g médian', t.gMed, +r[3]); cmp(nm + ' g réel médian', t.grMed, +r[4]); cmp(nm + ' écart médian', t.ecMed, +r[5]); cmp(nm + ' % prudent', t.prudent, +r[6]); cmp(nm + ' ρ', t.rho, +r[7]); };
      U.forEach(u => chk(u, 'TOUS', A.rows));
      A.BLOCS.forEach(b => chk('tous', b, A.rows.filter(o => o.bloc === b)));
      const tbs = {}; U.forEach(u => (tbs[u] = A.testB(A.rows, null, u)));
      ref.B_annees.forEach(r => { const y = tbs[r[0]].years.find(z => z.a === +r[2]), h = r[1] === '1an' ? '1' : '3', nm = r[0] + ' ' + r[2] + ' ' + r[1]; if (!y) { out.tot++; out.lines.push('année absente : ' + nm); return; } cmp(nm + ' n', h === '1' ? y.n : y.n3, +r[3]); cmp(nm + ' Q1', y['q1x' + h], +r[4]); cmp(nm + ' Q4', y['q4x' + h], +r[5]); });
      const qa = {}; ref.B_quartiles.forEach(r => (qa[r[0] + '|' + r[1] + '|' + r[2] + '|' + r[3]] = r));
      const addQ = (u, lab, list) => A.testB(list, null, u).quart.forEach(q => ['1', '3'].forEach(h => {
        const n = h === '1' ? q.n : q.n3, x = q['x' + h], hz = h === '1' ? '1an' : '3ans', r = qa[u + '|' + hz + '|' + lab + '|Q' + (q.q + 1)], nm = u + ' ' + lab + ' Q' + (q.q + 1) + ' ' + hz;
        if (!r) { if (n === 0) return; out.tot++; out.lines.push('quartile absent : ' + nm); return; }
        cmp(nm + ' n', n, +r[4]); cmp(nm + ' excès', x, +r[5]);
      }));
      U.forEach(u => { addQ(u, 'TOUS (quartiles par bloc)', A.rows); A.BLOCS.forEach(b => addQ(u, b, A.rows.filter(o => o.bloc === b))); });
    });
    return out;
  }

  A.pages.qualite = {
    render(main) {
      const bad = A.rows.filter(o => o.g != null && o.g < -0.12).sort((x, y) => x.g - y.g);
      const dups = A.rows.filter(o => o.dup).sort((x, y) => x.t.localeCompare(y.t) || x.a - y.a);
      const dout = A.rows.filter(o => o.sp === 1);
      const man = A.M.manuel;
      const med = A.YEARS.map(y => { const L = A.rows.filter(o => o.a === y); return { y, n: L.length, p: L.filter(o => o.sp === 2).length, g: L.filter(o => o.g != null).length, ta: L.filter(o => o.g != null && o.gr != null).length }; });
      const chk = selfCheck(A.M.a14_ref, f => A.atPrime(0.05, true, f));
      const stT = (obj, tot) => tbl(['Statut', 'Lignes', 'Part'], Object.entries(obj).map(([k, v]) => `<tr><td class="l">${esc(k.replace(/_/g, ' '))}</td><td>${nf(v, 0)}</td><td>${nf(v / tot * 100, 1)} %</td></tr>`));
      main.innerHTML = `
      <section class="sec"><div class="eyebrow">Confiance</div><h1>Qualité des données</h1>
        <p class="lede">Ce qui est exclu, ce qui est douteux, ce qui a été corrigé à la main, et la preuve que cette application recalcule exactement les résultats du pipeline Python.</p></section>
      <section class="sec"><h2>Contrôle contre le pipeline Python (les scripts a01 à a14 qui ont produit les données)</h2>
        <div class="story" style="border-left-color:${chk.ok === chk.tot ? 'var(--s3)' : 'var(--neg)'}"><b>${chk.ok === chk.tot ? '✓ ' : '✗ '}${chk.ok} valeurs sur ${chk.tot} identiques</b> aux fichiers backtest_A_blocs, backtest_B_annees et backtest_B_quartiles (WACC avec prime de risque 5 %, cycliques +1 pt, trois univers : tous, membres du S&amp;P 500, hors indice ; tolérance 10⁻⁴ car les montants sont arrondis à 4 décimales dans data.js, écart maximal ${nf(chk.maxd * 1e6, 1)} × 10⁻⁶). Ce contrôle se fait toujours avec ces réglages, quel que soit le curseur.${chk.lines.length ? '<br>Différences : ' + chk.lines.slice(0, 8).map(esc).join(' ; ') : ''}</div></section>
      <section class="grid g2">
        <div class="card"><h3>Lignes avec cours (${nf(P.prix_lignes, 0)})</h3>${stT(P.prix_statuts, P.prix_lignes)}<p class="note">Sans cours : la société n'est plus cotée sous ce ticker (rachat, faillite) ou le cours est antérieur à l'historique.</p></div>
        <div class="card"><h3>Lignes avec g (${nf(P.g_lignes, 0)})</h3>${stT(P.g_statuts, P.g_lignes)}<p class="note">« fcf trop faible » : FCF sous ${pc(A.M.params.FCF_MIN_RELATIF, 0)} de la VE ou négatif. g serait presque égal à r quel que soit le prix, il n'est pas calculé.</p></div>
      </section>
      <section class="sec"><h2>Couverture par année</h2><div class="grid g2"><div class="card"><h3>Lignes par étape <span class="legend"><span><i class="sw bar" style="background:var(--s1)"></i>avec cours</span><span><i class="sw" style="background:var(--s2)"></i>avec g</span></span></h3><div id="q-cov"></div></div>
        <div class="card"><h3>Lignes du test A par année <span class="legend"><span><i class="sw bar" style="background:var(--s3)"></i>FCF réel connu</span></span></h3><div id="q-ta"></div><p class="note">Le test A demande 4 ans de FCF après la clôture : les années récentes sont vides.</p></div></div>
        <p class="note">Les ${nf(P.fondamentaux_cik, 0)} sociétés viennent du S&amp;P 500 actuel et passé, mais les sociétés disparues ont souvent perdu leur ticker : la couverture par année est visible sur le graphique ci-dessus (biais du survivant). Catégories : ${Object.entries(P.categories_cik).map(([k, v]) => k + ' ' + v).join(' · ')}.</p></section>
      <section class="sec"><h2>Doublons (ticker, année) parmi les lignes avec g : ${dups.length}</h2><p>Une même société a parfois deux CIK (ancien et nouveau numéro SEC) et deux lignes la même année. Les doublons repérés sont exclus du calcul de g (exclusions_manuelles.csv, raison « doublon ») : il n'en reste aucun parmi les lignes avec g. Ce tableau ne liste que ceux qui auraient un g.</p>
        ${dups.length ? tbl(['Société', 'Année', 'CIK', 'VE', 'FCF retenu', 'g', 'Note'], dups.map(o => `<tr><td>${A.link(o.t)}</td><td>${o.a}</td><td>${esc(o.cik)}</td><td>${fM(o.ve)}</td><td>${fM(o.fcfr)}</td><td>${sp(o.g)}</td><td class="l">${esc(o.vf || '')}</td></tr>`), 'maxh') : ''}</section>
      <section class="sec"><h2>${(man.exclusions || []).length ? man.exclusions.length + ' lignes exclues à la main' : 'Valeurs suspectes repérées par un audit indépendant'}</h2><p>Un audit a recalculé toutes les lignes (aucun écart avec les CSV) puis repéré des erreurs de source probables : cours d'un autre titre, nombre d'actions d'une seule classe, regroupements d'actions. Ces lignes sont exclues du calcul de g (fichier exclusions_manuelles.csv) et un contrôle automatique (a15) vérifie qu'il n'en reste pas d'autres.</p>
        ${(man.exclusions || []).length ? tbl(['Société', 'CIK', 'Année', 'Raison'], man.exclusions.map(r => `<tr><td class="l">${esc(r[2])}</td><td class="l">${esc(r[0])}</td><td>${esc(r[1])}</td><td class="l" style="white-space:normal">${esc(r[3])}</td></tr>`), 'maxh') : '<p class="note">Fichier exclusions_manuelles.csv absent : lance a12 puis régénère les données.</p>'}
        <p class="note">Couverture : des années manquent pour certaines sociétés (lignes non exploitables, capex absent), dont NVDA 2013–2021 et Alphabet 2013–2020 : les plus grosses capitalisations ont parfois une série tronquée.</p></section>
      <section class="sec"><h2>${bad.length} lignes à revoir : g inférieur à −12 %</h2><p>Un g très négatif signifie que le prix est très bas par rapport au FCF : vrai pessimisme, FCF de pic, ou donnée fausse (nombre d'actions, dette). À vérifier une par une.</p>
        ${tbl(['Société', 'Année', 'Bloc', 'Prix', 'Actions (M)', 'VE', 'FCF retenu', 'g'], bad.map(o => `<tr class="click" onclick="A.ps.ent={t:'${esc(o.t)}',year:${o.a}};location.hash='#/entreprise/${encodeURIComponent(o.t)}'"><td>${esc(o.t)}</td><td>${o.a}</td><td class="l">${esc(A.blocLabel(o.bloc))}</td><td>${A.usd(o.px)}</td><td>${nf(o.sh, 1)}</td><td>${fM(o.ve)}</td><td>${fM(o.fcfr)}</td><td>${sp(o.g)}</td></tr>`), 'maxh')}</section>
      <section class="sec"><h2>${dout.length} cours douteux</h2><p>Cours marqué « douteux » par les contrôles de a10 : il ne sert pas au calcul de g.</p>${dout.length ? tbl(['Société', 'Année', 'Prix', 'Détail'], dout.map(o => `<tr><td>${A.link(o.t)}</td><td>${o.a}</td><td>${A.usd(o.px)}</td><td class="l">${esc(o.vf || '')}</td></tr>`), 'maxh') : ''}</section>
      <section class="sec"><h2>Corrections manuelles</h2><div class="grid g2">
        <details><summary>Catégories forcées (${man.classification.length}) : Standard, Cyclique, ou exclue (Non applicable)</summary>${tbl(['CIK', 'Catégorie', 'Raison'], man.classification.map(r => `<tr><td>${esc(r[0])}</td><td class="l">${esc(r[1])}</td><td class="l" style="white-space:normal">${esc(r[2])}</td></tr>`))}</details>
        <details><summary>Blocs forcés (${man.secteur.length})</summary>${tbl(['CIK', 'Bloc', 'Raison'], man.secteur.map(r => `<tr><td>${esc(r[0])}</td><td class="l">${esc(A.blocLabel(r[1]))}</td><td class="l" style="white-space:normal">${esc(r[2])}</td></tr>`))}</details>
        <details><summary>Tickers corrigés (${man.ticker.length})</summary>${tbl(['CIK', 'Ticker', 'Raison'], man.ticker.map(r => `<tr><td>${esc(r[0])}</td><td class="l">${esc(r[1])}</td><td class="l" style="white-space:normal">${esc(r[2])}</td></tr>`))}</details>
        <details><summary>Alertes de prix (${man.alertes_prix.length}) : problèmes repérés pendant la recherche des cours</summary>${tbl(['CIK', 'Ticker', 'Alerte'], man.alertes_prix.map(r => `<tr><td>${esc(r[0])}</td><td class="l">${esc(r[1])}</td><td class="l" style="white-space:normal">${esc(r[2])}</td></tr>`), 'maxh')}</details>
      </div><p class="note">Dettes saisies à la main : ${man.dette_n} lignes (colonne « statut dette » = manuelle). Lignes exclues du calcul de g : ${A.M.params.EXCLUSIONS.length} (voir le tableau plus haut).</p></section>`;
      A.lineChart($('q-cov'), { xs: A.YEARS, label: 'Couverture', h: 200, zero: true, yfmt: t => nf(t, 0), series: [{ kind: 'bar', color: 'var(--s1)', v: med.map(m => m.p) }, { kind: 'line', color: 'var(--s2)', v: med.map(m => m.g) }], tip: i => `<b>${med[i].y}</b><br>${nf(med[i].n, 0)} lignes de fondamentaux<br>${nf(med[i].p, 0)} avec cours<br>${nf(med[i].g, 0)} avec g` });
      A.lineChart($('q-ta'), { xs: A.YEARS, label: 'Lignes test A', h: 200, zero: true, yfmt: t => nf(t, 0), series: [{ kind: 'bar', color: 'var(--s3)', v: med.map(m => m.ta) }], tip: i => `<b>${med[i].y}</b><br>${nf(med[i].ta, 0)} lignes testées` });
    }
  };

  // ================= MÉTHODE =================
  A.pages.methode = {
    render(main) {
      const p = A.M.params, T = A.summaryTests(A.rows), ec = A.BLOCS.map(b => ({ b, t: A.testA(A.rows.filter(o => o.bloc === b)) })).filter(x => x.t.n).sort((x, y) => y.t.ecMed - x.t.ecMed);
      const concl = `Avec ${A.rTxt()} : le g implicite contient une information réelle mais modérée. Un g plus haut va de pair avec une croissance du FCF plus haute (ρ = ${nf(T.a.rho, 2)}, qui varie à peine quand r change ; la base de croissance est le FCFF de N−1, pas celui de N qui sert déjà à calculer g). L'écart entre croissance réelle et g est le plus grand pour ${ec.slice(0, 3).map(x => A.blocLabel(x.b) + ' (' + A.pts(x.t.ecMed) + ')').join(', ')} et le plus faible pour ${ec.slice(-3).map(x => A.blocLabel(x.b) + ' (' + A.pts(x.t.ecMed) + ')').join(', ')}. Côté sélection d'actions, le résultat est ambigu : les g bas ont rapporté plus que les g hauts ${T.p1} années sur ${T.ny} à 1 an et ${T.p3} sur ${T.ny3} à 3 ans (univers : ${A.state.univ === 'tous' ? 'toutes les sociétés' : A.state.univ === 'membres' ? 'membres du S&amp;P 500 à la date' : 'hors indice'}). L'écart n'est pas significatif et change de signe selon l'univers (page Backtest). Avec 13 à 15 années non indépendantes et sans coûts de transaction, on ne peut conclure ni à un signal ni à son absence.`;
      main.innerHTML = `
      <section class="sec"><div class="eyebrow">Comprendre</div><h1>La méthode</h1>
        <p class="lede">Un calcul de valeur à l'envers : au lieu de deviner la croissance pour trouver un prix, on part du prix et on cherche la croissance qu'il suppose.</p></section>
      <section class="sec"><h2>La formule</h2>
        <div class="card"><div class="eq" style="font-size:15px">VE = FCF × (1 + g) / (r − g)</div><p class="note" style="margin-top:8px">Une entreprise qui dégage un FCF aujourd'hui, qui le fait croître de g par an pour toujours, et dont on exige un rendement r, vaut VE. Calcul : VE(r − g) = FCF(1 + g), donc VE·r − FCF = g(VE + FCF). La formule demande r &gt; g, sinon la valeur est infinie. « Perpétuelle » : le flux dure pour toujours, d'où ce modèle à un seul étage. En isolant g :</p><div class="eq" style="font-size:15px;margin-top:6px">g = (VE × r − FCF) / (VE + FCF)</div></div>
        <div class="keys">
          <div><b>VE, valeur d'entreprise</b>Capitalisation boursière (prix × actions) + dette − trésorerie. C'est le prix de l'entreprise entière, dettes comprises.</div>
          <div><b>FCFF, flux de trésorerie libre avant intérêts</b>Cash opérationnel (OCF) + intérêts payés × (1 − impôt) − investissements (capex : usines, matériel, logiciels). On rajoute les intérêts après impôt parce que le WACC s'applique à un flux disponible pour les prêteurs comme pour les actionnaires. Intérêts non publiés : estimés par dette × 5 % quand une dette est publiée (colonne interest_source), sinon comptés pour 0. La trésorerie comprend aussi les placements à court terme et les titres non courants (jamais les participations).</div>
          <div><b>r, le taux d'actualisation</b>Une hypothèse, pas une mesure. C'est un WACC de marché par année : E/V × (taux du Trésor à 10 ans + prime de risque) + D/V × (taux à 10 ans + écart de crédit de 1,5 point) × (1 − impôt de 35 % jusqu'en 2017, 21 % ensuite). E/V et D/V sont les sommes des capitalisations et des dettes de l'échantillon, année par année ; le taux à 10 ans (FRED, DGS10) est le dernier connu à la date de clôture de chaque ligne. 2026 reprend la structure de 2025. Pas de bêta par société. Le curseur règle la prime de risque (5 % par défaut) ; la case « r fixe 9 % » remet l'ancienne méthode. WACC médian actuel : ${pc(A.state.rShow)}.</div>
          <div><b>g implicite</b>La croissance perpétuelle du FCF que le prix de marché suppose, pour ce r. Ce n'est ni une prévision, ni la croissance réelle (page Backtest) : c'est une lecture du prix. Il peut être négatif quand le prix est bas par rapport au FCF.</div>
        </div></section>
      <section class="sec"><h2>Les étapes du pipeline</h2>
        ${tbl(['Étape', 'Script', 'Ce qu\'elle fait', 'Résultat'], [
          ['1', 'a01–a08', 'Téléchargement des états financiers SEC (Companyfacts), extraction de l\'OCF, du capex, de la dette, de la trésorerie, des actions', 'fondamentaux_sp500.csv · ' + nf(P.fondamentaux_lignes, 0) + ' lignes, ' + nf(P.fondamentaux_cik, 0) + ' sociétés'],
          ['2', 'a09', 'Secteur de chaque société (code SIC de la SEC) et regroupement en blocs', 'secteur.csv'],
          ['3', 'a10', 'Cours de clôture à la date d\'exercice (Yahoo, puis Tiingo), cours ajustés des splits et des dividendes (rendement total)', 'prix_cloture.csv · ' + nf(P.prix_statuts.ok, 0) + ' lignes ok'],
          ['4', 'a11–a12', 'VE (a11), FCF retenu (moyenne sur ' + p.ANNEES_LISSAGE_CYCLIQUE + ' ans pour les cycliques) et g implicite (a12)', 'valeur_entreprise.csv, g_implicite.csv · ' + nf(P.g_statuts.ok, 0) + ' lignes ok'],
          ['5', 'a13', 'Tableau de bord par bloc', 'tableau de bord'],
          ['6', 'a14', 'Backtest : test A (FCF réel) et test B (rendement des actions)', 'backtest_*.csv']
        ].map(r => `<tr><td>${r[0]}</td><td class="l">${r[1]}</td><td class="l" style="white-space:normal">${r[2]}</td><td class="l" style="white-space:normal">${r[3]}</td></tr>`))}
      </section>
      <section class="sec"><h2>Les deux tests</h2><div class="grid g2">
        <div class="card"><h3>Test A · le FCF</h3><p class="note" style="max-width:none">Pour une clôture N : FCFF de N−1 (le dernier exercice connu à la clôture : on n'utilise pas N, qui sert déjà à calculer g) contre FCFF moyen de N+2 à N+4. La moyenne de N+2 à N+4 est centrée sur N+3, soit 4 ans après N−1 : « annualisé » veut dire (FCFF moyen N+2..N+4 / FCFF de N−1)^(1/4) − 1. Les deux flux doivent être positifs (sinon pas de taux de croissance fiable) et la moyenne future exige les trois années. Pour les sociétés cycliques, g repose sur une moyenne de 5 ans : la base est donc la moyenne du FCFF de N−5 à N−1 (au moins 3 valeurs), centrée sur N−3, et la croissance est annualisée sur 6 ans. Les FCFF des lignes exclues à la main ne servent ni de base ni de cible. Mesure : médiane de l'écart, part des cas où le FCF a fait mieux que prévu, corrélation de rang de Spearman entre g et la croissance réelle.</p></div>
        <div class="card"><h3>Test B · l'argent gagné</h3><p class="note" style="max-width:none">On range les sociétés en quatre quartiles de FCF / VE (dans chaque bloc et chaque année) : à date donnée c'est le même classement que g, mais sans dépendre du taux à 10 ans de la date de clôture. On part du premier jour de bourse après le dépôt du 10-K (le FCFF n'est public qu'à ce moment) et on suit le rendement total, dividendes inclus (cours ajusté des splits et des dividendes), 1 an (départ + 365 jours) et 3 ans (+ 1 095 jours) plus tard, après avoir limité chaque rendement aux percentiles 1 % et 99 % de son année, et on retranche la médiane de l'année dans l'univers considéré (« excès »). Le quartile est formé avec la valeur d'entreprise à la clôture, connue avant le départ. Q1 = g le plus bas (FCF/VE le plus haut), Q4 = g le plus haut. Univers de référence : sociétés membres du S&amp;P 500 à la date de clôture (par CIK), « hors indice » et « toutes » servent de contrôle. « 3 ans annualisé » = rendement cumulé converti en taux par an.</p><p class="note" style="max-width:none;margin-top:6px">Deux versions : (1) par année sur tout le marché (au moins 100 lignes par année) : c'est elle qui donne le décompte « X années sur 15 (1 an) ou 13 (3 ans) ». (2) Par bloc et par année (au moins 8 lignes) : pour comparer des sociétés du même secteur, c'est celle de la page Blocs et des barres de la page Backtest.</p></div></div></section>
      <section class="sec"><h2>Ce qu'on en conclut</h2>
        <div class="story">${concl}</div></section>
      <section class="sec"><h2>Les limites</h2><div class="keys">
        <div><b>Modèle à un seul étage</b>Une croissance constante pour toujours est une simplification : g résume la croissance moyenne attendue, pas une trajectoire.</div>
        <div><b>Choix de r</b>Tous les g bougent avec r. La page Backtest montre ce qui change quand la prime de risque passe de 3 % à 8 %, et avec l'ancien r fixe de 9 %.</div>
        <div><b>Biais du survivant</b>Les sociétés disparues sans ticker utilisable manquent, surtout avant 2015.</div>
        <div><b>FCF d'une seule année</b>Un FCF de pic ou de creux fausse g, d'où la moyenne sur ${p.ANNEES_LISSAGE_CYCLIQUE} ans pour les cycliques.</div>
        <div><b>Date de dépôt estimée</b>Pour environ 7 % des lignes du test B (497 sur 7 276), la date de dépôt du 10-K manque ou est incohérente : le départ est alors la clôture + 90 jours (colonne depart_estime de backtest_lignes.csv). Sans ces lignes, aucune conclusion du test B ne change.</div>
        <div><b>Biais du survivant, sens probable</b>Les sociétés disparues ont plutôt fait moins bien : rendements et croissance réelle sont probablement surestimés. Le test A exige un FCFF positif en N−1 (moyenne N−5 à N−1 pour les cycliques) et en moyenne N+2 à N+4, ce qui écarte aussi les sociétés dont le FCF s'est dégradé.</div>
        <div><b>Date du cours</b>Le cours de la VE et de g est pris à la clôture de l'exercice, alors que les comptes sortent 1 à 3 mois plus tard : g est une lecture du prix, pas un signal exploitable à cette date. Le test B, lui, part après le dépôt du 10-K.</div>
        <div><b>Pas des tests statistiques</b>Les 13 à 15 années partagent le même marché et les rendements à 3 ans se chevauchent : « X années sur 15 » est un décompte, pas une preuve. Les valeurs sont nominales (non corrigées de l'inflation).</div>
        <div><b>VE contre FCF</b>La VE inclut la dette, le FCF est calculé après intérêts : approximation. Rachats d'actions, rémunération en actions, loyers et acquisitions ne sont pas traités.</div>
        <div><b>Pas une recommandation</b>Projet d'étude. Rien ici n'est un conseil d'investissement.</div></div></section>
      <section class="sec"><h2>Glossaire</h2><div class="keys">
        <div><b>CIK</b>Numéro d'identification d'une société à la SEC.</div>
        <div><b>SIC</b>Code d'activité à 4 chiffres utilisé par la SEC.</div>
        <div><b>Capex</b>Dépenses d'investissement (usines, matériel, logiciels activés).</div>
        <div><b>Quartile</b>Un quart des sociétés rangées par g : Q1 les plus bas, Q4 les plus hauts.</div>
        <div><b>Corrélation de rang (ρ)</b>De −1 à +1 : mesure si les sociétés rangées par g le sont dans le même ordre par croissance réelle. 0 = aucun lien.</div>
        <div><b>Excès de rendement</b>Rendement de l'action moins le rendement de la société médiane de l'échantillon cette année-là.</div>
        <div><b>Cyclique</b>Société dont le FCF fluctue fortement avec la conjoncture : moyenne sur 5 ans et r +1 point.</div>
        <div><b>OCF</b>Cash généré par l'activité, avant investissements.</div>
        <div><b>Capitalisation</b>Cours × nombre d'actions.</div>
        <div><b>Split</b>Division d'actions : le cours est divisé, la valeur de la société ne change pas.</div>
        <div><b>Médiane</b>Valeur du milieu, moins sensible aux extrêmes que la moyenne.</div>
        <div><b>Centile, décile</b>Le 25e centile est la valeur sous laquelle se trouvent 25 % des sociétés ; un décile est un dixième.</div>
        <div><b>Backtest</b>Test sur le passé : on regarde ce qui s'est réellement passé après chaque date.</div>
        <div><b>Biais du survivant</b>On ne voit que les sociétés encore cotées, qui ont plutôt mieux réussi.</div>
        <div><b>Points de pourcentage (pts)</b>Différence entre deux taux : 7 % moins 4 % = 3 pts.</div>
        <div><b>Ticker, SEC, S&amp;P 500</b>Code boursier d'une action ; autorité des marchés américaine ; indice des 500 grandes sociétés cotées aux États-Unis.</div></div></section>`;
    }
  };
})();
