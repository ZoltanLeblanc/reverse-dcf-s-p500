"""build_data.py : fabrique data/data.js (les données de l'interface) à partir des CSV.
Lancer depuis ce dossier :  py build_data.py
Par défaut, il lit les CSV dans ..\Python (le dossier voisin). Autre dossier : py build_data.py "C:\chemin\vers\Python"
Entrées : prix_cloture, fondamentaux_sp500, valeur_entreprise, g_implicite, secteur, backtest_lignes, cik_categorie
et les tables manuelles (.csv) ; a12_g_implicite.py est lu pour en afficher les paramètres. Sortie : data/data.js.
Fonctions : lire (CSV du dossier d'entrée), num / millions (arrondi, conversion en millions de dollars),
structure_wacc (E/V et D/V par année), main (assemble sociétés, lignes et métadonnées, écrit data.js).
"""

import sys, os, re, json, datetime
import pandas as pd

DOSSIER_CSV = sys.argv[1] if len(sys.argv) > 1 else os.path.join('..', 'Python')
SORTIE = os.path.join('data', 'data.js')
M = 1e6  # les montants sont stockés en millions de dollars


def lire(nom, **kw):
    if not os.path.exists(os.path.join(DOSSIER_CSV, nom)):
        raise SystemExit(nom + ' absent de ' + DOSSIER_CSV + ' : relancer la chaine a06 a a15 (voir README)')
    return pd.read_csv(os.path.join(DOSSIER_CSV, nom), dtype={'cik': str, 'sic': str}, **kw)


def num(v, d=4):
    if v is None or pd.isna(v):
        return None
    return round(float(v), d)


def millions(v):
    return num(v / M, 4) if v is not None and not pd.isna(v) else None


def structure_wacc(ve):
    """E/V et D/V par année : sommes des capitalisations et des dettes brutes (lignes avec les deux), comme a12 ; 2026 reprend 2025."""
    t = ve.dropna(subset=['capitalisation', 'dette'])
    s = t.groupby('annee')[['capitalisation', 'dette']].sum()
    out = {int(a): [float(r.capitalisation / (r.capitalisation + r.dette)), float(r.dette / (r.capitalisation + r.dette))] for a, r in s.iterrows()}
    if 2026 in out and 2025 in out:
        out[2026] = out[2025]
    return out


def main():
    px = lire('prix_cloture.csv')
    fd = lire('fondamentaux_sp500.csv')
    ve = lire('valeur_entreprise.csv')
    gi = lire('g_implicite.csv')
    sec = lire('secteur.csv')
    bt = lire('backtest_lignes.csv')
    cat = lire('cik_categorie.csv')
    for t in (px, fd, ve, gi, bt):
        t['annee'] = t['annee'].astype(int)
    key = ['cik', 'annee']
    d = px.merge(fd[key + ['revenue', 'ebit', 'ocf', 'capex', 'interest', 'dette_statut']], on=key, how='left')
    d = d.merge(ve[key + ['dette', 'cash', 'valeur_entreprise']], on=key, how='left')
    d = d.merge(gi[key + ['fcf', 'taux_10_ans', 'r', 'g_implicite', 'statut']].rename(columns={'statut': 'statut_g', 'fcf': 'fcf_retenu'}), on=key, how='left')
    d = d.merge(bt[key + ['fcf_avant', 'fcf_apres', 'g_reel', 'ret1', 'ret3_ann', 'exc1', 'exc3', 'membre']], on=key, how='left')
    d['impot'] = d['annee'].map(lambda a: 0.35 if a <= 2017 else 0.21)
    d['ia'] = d['interest'].fillna(0).abs() * (1 - d['impot'])  # intérêts après impôt (a12 : intérêts absents = 0)

    # ---- entreprises : une par CIK, nom affiché = ticker (suffixe (cik) si deux sociétés différentes partagent un ticker)
    secx = sec.set_index('cik')
    ciks = sorted(d['cik'].unique(), key=lambda c: (secx.loc[c, 'ticker'] if c in secx.index else 'ZZZ', c))
    tick_par_cik = {c: d[d.cik == c]['ticker'].iloc[0] for c in ciks}
    annees_par_cik = {c: set(d[d.cik == c]['annee']) for c in ciks}
    par_ticker = {}
    for c in ciks:
        par_ticker.setdefault(tick_par_cik[c], []).append(c)
    affiche = {}
    for t, lst in par_ticker.items():
        conflit = False
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                if annees_par_cik[lst[i]] & annees_par_cik[lst[j]]:
                    conflit = True
        for c in lst:
            affiche[c] = '%s (%s)' % (t, c) if conflit else t
    companies, idx = [], {}
    for c in ciks:
        s = secx.loc[c] if c in secx.index else None
        companies.append([affiche[c], c, s['bloc'] if s is not None else None, s['categorie'] if s is not None else d[d.cik == c]['categorie'].iloc[0],
                          str(s['sic']) if s is not None else None, s['sic_description'] if s is not None else None, s['source'] if s is not None else None])
        idx[c] = len(companies) - 1

    d['doublon'] = d.duplicated(['ticker', 'annee'], keep=False) & d['g_implicite'].notna()
    sp_list = sorted(d['statut'].dropna().unique().tolist())
    sg_list = ['ok', 'fcf trop faible', 'fcf indisponible', 'exclu', 'VE negative']
    ds_list = sorted(d['dette_statut'].dropna().unique().tolist())
    cols = ['c', 'a', 'sp', 'sg', 'dc', 'px', 'pxa', 'sh', 'cap', 'dt', 'cs', 've', 'ocf', 'cpx', 'fcf', 'fcfr', 'rev', 'ebit',
            'gf', 'rf', 'gr', 'fa', 'fp', 'r1', 'r3', 'x1', 'x3', 'ds', 'vf', 'dup', 't10', 'ia', 'mb']
    rows = []
    d = d.sort_values(['cik', 'annee'])
    for r in d.itertuples(index=False):
        ocf = millions(r.ocf)
        cpx = millions(r.capex)
        sg = None if pd.isna(r.statut_g) else sg_list.index(r.statut_g)
        rows.append([
            idx[r.cik], int(r.annee), sp_list.index(r.statut), sg,
            None if pd.isna(r.date_cloture) else str(r.date_cloture),
            num(r.prix_epoque, 4), num(r.cours_yahoo, 4), millions(r.shares), millions(r.capitalisation), millions(r.dette), millions(r.cash),
            millions(r.valeur_entreprise), ocf, cpx, (round(ocf + millions(r.ia) - cpx, 4) if ocf is not None and cpx is not None else None),
            millions(r.fcf_retenu), millions(r.revenue), millions(r.ebit),
            num(r.g_implicite, 6), num(r.r, 4), num(r.g_reel, 6), millions(r.fcf_avant), millions(r.fcf_apres),
            num(r.ret1, 6), num(r.ret3_ann, 6), num(r.exc1, 6), num(r.exc3, 6),
            None if pd.isna(r.dette_statut) else ds_list.index(r.dette_statut),
            None if pd.isna(r.verifier) else str(r.verifier), 1 if r.doublon else 0, num(r.taux_10_ans, 5),
            millions(r.ia), (None if pd.isna(r.membre) else (1 if r.membre else 0))])

    # ---- paramètres lus dans a12 (s'il est là), pour les afficher dans la page Méthode
    params = {'TAUX_R': {'Standard': 0.09, 'Cyclique': 0.10}, 'ANNEES_LISSAGE_CYCLIQUE': 5, 'FCF_MIN_RELATIF': 0.01, 'EXCLUSIONS': []}
    p12 = os.path.join(DOSSIER_CSV, 'a12_g_implicite.py')
    if not os.path.exists(p12):
        p12 = os.path.join(DOSSIER_CSV, 'a12_g_implicite.py')
    if os.path.exists(p12):
        t = open(p12, encoding='utf-8').read()
        m = re.search(r"TAUX_R\s*=\s*\{([^}]*)\}", t)
        if m:
            params['TAUX_R'] = {k: float(v) for k, v in re.findall(r"'(\w+)'\s*:\s*([0-9.]+)", m.group(1))}
        m = re.search(r"ANNEES_LISSAGE_CYCLIQUE\s*=\s*(\d+)", t)
        if m: params['ANNEES_LISSAGE_CYCLIQUE'] = int(m.group(1))
        m = re.search(r"FCF_MIN_RELATIF\s*=\s*([0-9.]+)", t)
        if m: params['FCF_MIN_RELATIF'] = float(m.group(1))
        m = re.search(r"EXCLUSIONS\s*=\s*\{(.*?)\}", t, re.S)
        if m: params['EXCLUSIONS'] = [[a, b] for a, b in re.findall(r"\('(\d+)',\s*'(\d+)'\)", m.group(1))]
    pex = os.path.join(DOSSIER_CSV, 'exclusions_manuelles.csv')  # lignes exclues a la main (a12)
    if os.path.exists(pex):
        tex = pd.read_csv(pex, dtype=str).fillna('')
        params['EXCLUSIONS'] = [[str(int(a)), b] for a, b in zip(tex['cik'], tex['annee'])]

    def compter_lignes(nom):  # dette_manuelle.csv a une colonne source avec des virgules : on compte juste les lignes
        p = os.path.join(DOSSIER_CSV, nom)
        if not os.path.exists(p):
            return 0
        return max(0, sum(1 for l in open(p, encoding='utf-8-sig') if l.strip()) - 1)

    def table(nom):
        p = os.path.join(DOSSIER_CSV, nom)
        if not os.path.exists(p):
            return []
        t = pd.read_csv(p, dtype=str).fillna('')
        return t.values.tolist()

    cat_n = cat['categorie'].value_counts().to_dict()
    meta = {
        'cree': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'unite': 'millions de dollars',
        'cols': cols, 'statuts_prix': sp_list, 'statuts_g': sg_list, 'statuts_dette': ds_list,
        'params': params,
        'pipeline': {
            'fondamentaux_lignes': int(len(fd)), 'fondamentaux_cik': int(fd['cik'].nunique()),
            'categories_cik': cat_n,
            'prix_lignes': int(len(px)), 'prix_statuts': px['statut'].value_counts().to_dict(),
            've_lignes': int(len(ve)), 'g_lignes': int(len(gi)), 'g_statuts': gi['statut'].value_counts().to_dict(),
            'backtest_lignes': int(len(bt)), 'test_a': int(bt['g_reel'].notna().sum()),
            'test_b_1an': int(bt['exc1'].notna().sum()), 'test_b_3ans': int(bt['exc3'].notna().sum()),
        },
        'manuel': {
            'classification': table('classification_manuelle.csv'),
            'secteur': table('secteur_manuel.csv'),
            'ticker': table('ticker_manuel.csv'),
            'exclusions': table('exclusions_manuelles.csv'),
            'dette_n': compter_lignes('dette_manuelle.csv'),
            'alertes_prix': table('alertes_prix.csv'),
        },
        'wacc': structure_wacc(ve),
        'a14_ref': {  # résultats de a14 (WACC, prime 5 %), pour contrôle
            'A': table('backtest_A_blocs.csv'), 'B_annees': table('backtest_B_annees.csv'), 'B_quartiles': table('backtest_B_quartiles.csv'),
        },
    }
    os.makedirs('data', exist_ok=True)
    out = {'meta': meta, 'companies': companies, 'rows': rows}
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with open(SORTIE, 'w', encoding='utf-8') as f:
        f.write('window.RDCF = ')
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')
    print('Fait :', SORTIE, '|', len(companies), 'sociétés (CIK) |', len(rows), 'lignes |', round(os.path.getsize(SORTIE) / 1e6, 2), 'Mo')


if __name__ == '__main__':
    main()
