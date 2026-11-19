/* 06 : navigation et curseur r */
(function () {
  const A = window.A, $ = A.$;
  const ROUTES = [['accueil', 'Accueil'], ['entreprise', 'Entreprise'], ['marche', 'Marché'], ['blocs', 'Blocs'], ['backtest', 'Backtest'], ['qualite', 'Qualité'], ['methode', 'Méthode']];
  $('nav').innerHTML = ROUTES.map(r => `<a href="#/${r[0]}" data-r="${r[0]}">${r[1]}</a>`).join('');
  let cur = null;
  function route() {
    const parts = location.hash.replace(/^#\/?/, '').split('/'), name = A.pages[parts[0]] ? parts[0] : 'accueil'; let arg = ''; try { arg = parts[1] ? decodeURIComponent(parts[1]) : ''; } catch (e) { arg = parts[1] || ''; }
    cur = { name, arg };
    document.querySelectorAll('#nav a').forEach(a => { if (a.dataset.r === name) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    if (name === 'entreprise' && !arg) { const t = A.ps.ent && A.ps.ent.t || (A.byTicker.AAPL ? 'AAPL' : A.comp[0].t); location.replace('#/entreprise/' + encodeURIComponent(t)); return; }
    render();
    window.scrollTo(0, 0);
  }
  function render() {
    if (!cur) return;
    A.hideTip();
    try { A.pages[cur.name].render($('main'), cur.arg); document.title = 'Reverse DCF · ' + (cur.arg || cur.name); }
    catch (e) { $('main').innerHTML = '<section class="sec"><h1>Erreur</h1><p>' + A.esc(e.message) + '</p></section>'; console.error(e); }
  }
  const out = $('rrOut');
  const upd = () => { out.textContent = A.pc(A.state.prime, 1); };
  let tm;
  $('rr').addEventListener('input', e => { A.state.prime = +e.target.value; upd(); clearTimeout(tm); tm = setTimeout(() => { A.recompute(); const y = scrollY; render(); scrollTo(0, y); }, 150); });
  $('fix').addEventListener('change', e => { A.state.mode = e.target.checked ? 'fixe' : 'wacc'; A.state.r = 0.09; $('rr').disabled = e.target.checked; A.recompute(); const y = scrollY; render(); scrollTo(0, y); });
  $('cyc').addEventListener('change', e => { A.state.cyc = e.target.checked; A.recompute(); const y = scrollY; render(); scrollTo(0, y); });
  let rw = innerWidth, tr;
  addEventListener('resize', () => { if (innerWidth === rw) return; rw = innerWidth; clearTimeout(tr); tr = setTimeout(() => { const y = scrollY; render(); scrollTo(0, y); }, 150); });
  addEventListener('hashchange', route);
  upd(); route();
})();
