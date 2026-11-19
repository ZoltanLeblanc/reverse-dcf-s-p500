"""a14 - Backtest du g implicite : le marche avait-il raison ?

Entrees : g_implicite.csv, prix_cloture.csv, fondamentaux_sp500.csv, secteur.csv, ticker_cik_sp500.csv,
          ../Historique S&P500/S&P 500 Historical Components & Changes (Updated).csv
Sorties : backtest_lignes.csv, backtest_A_blocs.csv, backtest_B_quartiles.csv, backtest_B_annees.csv
A lancer depuis le dossier Python (chemins relatifs).

Choix de methode :
 - FCFF = OCF + interets x (1 - T) - capex, comme dans a12 (T = 35 % jusqu'en 2017, 21 % ensuite).
 - Test A : FCFF de N-1 (dernier exercice connu a la date de cloture) contre la moyenne des FCFF de N+2..N+4.
   Le centre de la fenetre (N+3) est a 4 ans de N-1 : la croissance annuelle est calculee sur 4 ans.
   Cyclique : base = moyenne des FCFF de N-5 a N-1 (au moins 3), centre N-3, croissance calculee sur 6 ans jusqu'au centre N+3.
 - Test B : quartiles de FCF / VE (le facteur "value"). Un FCF/VE eleve = un g implicite bas (meme taux r a une date donnee),
   donc Q1 = g le plus bas = FCF/VE le plus haut. Le taux a 10 ans de chaque ligne est celui de sa date de cloture :
   trier sur g melangerait des dates differentes, trier sur FCF/VE ne depend pas du taux.
 - Rendement total (cours ajuste des splits et dividendes) : depart = premier jour de bourse apres le depot du 10-K, puis +365 et +1 095 jours (a10).
   Le 1 an n'exige pas le cours a 3 ans. Le tri en quartiles reste fait sur FCFF/VE avec la VE a la cloture.
 - Societe membre du S&P 500 a la date de cloture : par CIK (pas par ticker), via ticker_cik_sp500.csv.
   Les conclusions portent sur les membres ; "tous" et "hors indice" servent de controle.

Fonctions principales :
 - lire_indice : lit la composition historique du S&P 500 (date, liste de tickers).
 - membres_par_cik : indique si chaque ligne appartient a l'indice a sa date de cloture.
 - charger : charge et filtre les CSV d'entree (g, prix, FCFF, secteurs).
 - valeur_a : decale une colonne annuelle pour retrouver le FCFF a N+k.
 - construire_lignes : calcule g reel, ecart, rendements et rendements en exces par ligne.
 - quartile : classe en quartiles de FCF/VE (Q1 = g le plus bas).
 - resume_A / resume_B : resumes du test A (par bloc) et du test B (quartiles, par annee).
 - t_newey_west : statistique t avec variance de Newey-West (poids de Bartlett).
 - synthese_B : synthese du test B (ecart Q1 - Q4, statistiques t).
 - main : enchaine le calcul et ecrit les quatre CSV de sortie.
"""

import os
import re
import numpy as np
import pandas as pd

from a01_ticker_CIK import charger_table_ticker_cik, resoudre_cik
from a12_g_implicite import impot, lire_exclusions

ANNEES_ENTRE_CENTRES = {'Standard': 4, 'Cyclique': 6}  # test A : Standard : de N-1 au centre de N+2..N+4 (N+3) = 4 ans ; Cyclique : de N-3 (centre de N-5..N-1) a N+3 = 6 ans
MIN_ANNEES_CYCLIQUE = 3    # test A cyclique : au moins 3 FCFF sur N-5..N-1, comme a12 (doit rester egal au minimum de a12.fcf_retenu)
MIN_BLOC_ANNEE = 8         # test B : un bloc doit avoir au moins 8 societes cette annee-la (2 par quartile)
WINSOR = (0.01, 0.99)     # test B : rendements limites aux percentiles 1 % et 99 % de chaque annee avant l'exces
ANNEES_NON_CHEVAUCHANTES = (2010, 2013, 2016, 2019, 2022)  # departs espaces de 3 ans : horizons a 3 ans sans recouvrement
MIN_ANNEE = 100            # test B : au moins 100 societes dans l'annee (ecarte les annees trop peu fournies)
CHEMIN_INDICE = os.path.join('..', 'Historique S&P500', 'S&P 500 Historical Components & Changes (Updated).csv')
UNIVERS = ('tous', 'membres', 'hors indice')


def lire_indice(chemin=CHEMIN_INDICE):
    """Liste triee de (date, liste de tickers). Format : une colonne contenant 'date,"T1,T2,..."'."""
    liste = []
    if not os.path.exists(chemin):
        raise SystemExit('Fichier de composition du S&P 500 absent : ' + chemin + ' (source tierce a fournir, voir README, section Donnees a fournir)')
    with open(chemin, 'r', encoding='utf-8-sig') as f:
        next(f)
        for ligne in f:
            ligne = ligne.strip().replace('""', '"').strip('"')
            m = re.match(r'(\d{4}-\d{2}-\d{2}),"?(.*?)"?$', ligne)
            if m:
                liste.append((pd.Timestamp(m.group(1)), m.group(2).replace('"', '').split(',')))
    liste.sort(key=lambda x: x[0])
    return liste


def membres_par_cik(dates, ciks, liste=None, table=None):
    """True si le CIK de la ligne figure dans la derniere composition connue avant la date de cloture (NaN si pas de date)."""
    liste = liste if liste is not None else lire_indice()
    table = table if table is not None else charger_table_ticker_cik('ticker_cik_sp500.csv')
    dates_idx = [d for d, _ in liste]
    cache = {}
    sortie = []
    for dt, cik in zip(dates, ciks):
        if pd.isna(dt):
            sortie.append(np.nan)
            continue
        i = np.searchsorted(dates_idx, dt, side='right') - 1
        if i < 0:
            sortie.append(np.nan)
            continue
        if i not in cache:
            ref = liste[i][0].to_pydatetime()
            cache[i] = {resoudre_cik(table, t, ref) for t in liste[i][1]} - {None}
        sortie.append(str(int(cik)) in {str(int(c)) for c in cache[i]})
    return sortie


def charger():
    g = pd.read_csv('g_implicite.csv', dtype={'cik': str})
    g = g[g['statut'] == 'ok'][['cik', 'annee', 'ticker', 'categorie', 'valeur_entreprise', 'fcf', 'g_implicite']].copy()
    g['fcf_sur_ve'] = g['fcf'] / g['valeur_entreprise']
    p = pd.read_csv('prix_cloture.csv', dtype={'cik': str})
    p = p[p['statut'] == 'ok'][['cik', 'annee', 'date_cloture', 'date_cours', 'cours_yahoo', 'date_depart', 'ajuste_depart', 'ajuste_h1', 'ajuste_h3']].dropna(subset=['cours_yahoo', 'date_cours'])
    p['date_cloture'] = pd.to_datetime(p['date_cloture'])
    p['date_cours'] = pd.to_datetime(p['date_cours'])
    p['date_depart'] = pd.to_datetime(p['date_depart'])
    fe = pd.read_csv('fondamentaux_sp500.csv', dtype={'cik': str, 'depart_estime': str})
    if 'depart_estime' not in fe.columns:
        raise SystemExit('a14 : colonne depart_estime absente de fondamentaux_sp500.csv (relancer a06)')
    fe = fe[['cik', 'annee', 'depart_estime']]
    p = p.merge(fe, on=['cik', 'annee'], how='left')
    if p['depart_estime'].isna().any():
        print('ATTENTION a14 : ' + str(int(p['depart_estime'].isna().sum())) + ' lignes de prix sans ligne dans fondamentaux_sp500.csv (depart_estime inconnu)')   # 'oui' : date de depot inconnue, depart estime a la cloture + 90 jours (audit seulement)
    f = pd.read_csv('fondamentaux_sp500.csv', dtype={'cik': str})
    t = f['annee'].map(impot)
    f['fcf'] = f['ocf'] + f['interest'].fillna(0).abs() * (1 - t) - f['capex']   # FCFF
    f = f[['cik', 'annee', 'fcf']].dropna()
    exclues = lire_exclusions()   # un FCFF exclu pour donnee fausse ne sert ni de base ni de cible
    f = f[[(str(int(c)), str(a)) not in exclues for c, a in zip(f['cik'], f['annee'])]]
    s = pd.read_csv('secteur.csv', dtype={'cik': str})[['cik', 'bloc']]
    return g, p, f, s


def valeur_a(table, colonne, decalage):
    # renvoie, pour chaque (cik, annee), la valeur de `colonne` a l'annee annee + decalage
    t = table[['cik', 'annee', colonne]].copy()
    t['annee'] = t['annee'] - decalage
    return t.rename(columns={colonne: f'{colonne}_{decalage:+d}'})


def construire_lignes(g, p, f, s):
    d = g.merge(s, on='cik', how='left')

    # --- Test A : croissance reelle du FCFF ---
    for k in (-5, -4, -3, -2, -1, 2, 3, 4):
        d = d.merge(valeur_a(f, 'fcf', k), on=['cik', 'annee'], how='left')
    passes = d[['fcf_-5', 'fcf_-4', 'fcf_-3', 'fcf_-2', 'fcf_-1']]
    moyenne5 = passes.mean(axis=1).where(passes.notna().sum(axis=1) >= MIN_ANNEES_CYCLIQUE)
    d['fcf_avant'] = np.where(d['categorie'] == 'Cyclique', moyenne5, d['fcf_-1'])   # Cyclique : moyenne N-5..N-1 (a12 lisse N-4..N : decalage d'un an, sans effet sur les resultats)
    d = d.drop(columns=['fcf_-5', 'fcf_-4', 'fcf_-3', 'fcf_-2', 'fcf_-1'])
    d['fcf_apres'] = d[['fcf_+2', 'fcf_+3', 'fcf_+4']].mean(axis=1, skipna=False)
    d = d.drop(columns=['fcf_+2', 'fcf_+3', 'fcf_+4'])
    ok = (d['fcf_avant'] > 0) & (d['fcf_apres'] > 0)
    d['g_reel'] = (d['fcf_apres'] / d['fcf_avant']) ** (1 / d['categorie'].map(ANNEES_ENTRE_CENTRES)) - 1
    d.loc[~ok, 'g_reel'] = float('nan')
    d['ecart'] = d['g_reel'] - d['g_implicite']        # > 0 : le marche etait trop prudent

    # --- Test B : rendement total (cours ajuste des splits et des dividendes) a partir du premier jour de bourse apres le depot du 10-K ---
    # Departs et horizons (1 an = depart + 365 jours, 3 ans = depart + 1 095 jours) viennent d'a10, tous lus dans la meme serie de cours ; pas de repli sur le cours non ajuste.
    d = d.merge(p.rename(columns={'cours_yahoo': 'cours_0', 'date_cours': 'date_cours_0'}), on=['cik', 'annee'], how='left')
    d['ret1'] = d['ajuste_h1'] / d['ajuste_depart'] - 1
    d['ret3_ann'] = (d['ajuste_h3'] / d['ajuste_depart']) ** (1 / 3) - 1
    d = d.drop(columns=['ajuste_depart', 'ajuste_h1', 'ajuste_h3'])
    d['membre'] = membres_par_cik(d['date_cloture'], d['cik'])
    if d['membre'].isna().any():
        raise SystemExit('a14 : ' + str(int(d['membre'].isna().sum())) + ' lignes sans appartenance a l indice (date de cloture manquante ou anterieure a la premiere composition de l indice)')
    d['univers'] = d['membre'].map({True: 'membres', False: 'hors indice'}).fillna('hors indice')
    # rendement en exces = rendement - rendement median de toutes les societes cette annee-la
    for c, e in (('ret1', 'exc1'), ('ret3_ann', 'exc3')):
        d[e] = d[c] - d.groupby('annee')[c].transform('median')
    if d.duplicated(['cik', 'annee']).any():
        raise SystemExit('a14 : doublons (cik, annee) apres les fusions : ' + str(int(d.duplicated(['cik', 'annee']).sum())))
    if d['bloc'].isna().any():
        print('ATTENTION a14 : ' + str(int(d['bloc'].isna().sum())) + ' lignes sans bloc dans secteur.csv (absentes des quartiles par bloc)')
    return d


def quartile(serie):
    # Q1 = g le plus bas (FCF/VE le plus haut), Q4 = g le plus haut (FCF/VE le plus bas)
    return pd.qcut((-serie).rank(method='first'), 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])


def sous_univers(d, univers):
    return d if univers == 'tous' else d[d['univers'] == univers]


def resume_A(d):
    def stats(x):
        return pd.Series({
            'n': len(x),
            'g_implicite_median': x['g_implicite'].median(),
            'g_reel_median': x['g_reel'].median(),
            'ecart_median': x['ecart'].median(),
            'part_marche_trop_prudent': (x['ecart'] > 0).mean(),
            # correlation de rang : > 0 si un g implicite plus haut precede une croissance reelle plus haute
            'correlation_rang': x['g_implicite'].rank().corr(x['g_reel'].rank()),
        })
    a = d.dropna(subset=['g_reel'])
    blocs = a.groupby('bloc').apply(stats).reset_index().sort_values('n', ascending=False)
    blocs.insert(0, 'univers', 'tous')
    tout = []
    for u in UNIVERS:
        x = sous_univers(a, u)
        t = stats(x).to_frame().T
        t.insert(0, 'bloc', 'TOUS')
        t.insert(0, 'univers', u)
        tout.append(t)
    return pd.concat(tout + [blocs], ignore_index=True)


def resume_B(d):
    """Quartiles de FCF/VE dans chaque (bloc, annee) et par annee, pour chaque univers ; rendement en exces contre la mediane
    de l'univers considere. Les horizons 1 an et 3 ans sont traites separement (le 1 an n'exige pas le cours a 3 ans)."""
    lignes_q, lignes_a = [], []
    for u in UNIVERS:
        x = sous_univers(d, u)
        for hor, ret, nom_exc, nom_moy in (('1an', 'ret1', 'exc1', 'exc1_moyen'), ('3ans', 'ret3_ann', 'exc3', 'exc3_ann_moyen')):
            b = x.dropna(subset=[ret]).copy()
            b['ret_w'] = b.groupby('annee')[ret].transform(lambda s: s.clip(s.quantile(WINSOR[0]), s.quantile(WINSOR[1])))
            b['exc'] = b['ret_w'] - b.groupby('annee')['ret_w'].transform('median')   # exces winsorise (moyenne) ; la mediane est donnee a cote
            # quartiles dans chaque (bloc, annee)
            q = b[b.groupby(['bloc', 'annee'])['fcf_sur_ve'].transform('size') >= MIN_BLOC_ANNEE].copy()
            q['quartile'] = q.groupby(['bloc', 'annee'])['fcf_sur_ve'].transform(quartile)
            tous = q.groupby('quartile', observed=True)['exc'].agg(['size', 'mean', 'median']).reset_index()
            tous.insert(0, 'bloc', 'TOUS (quartiles par bloc)')
            blocs = q.groupby(['bloc', 'quartile'], observed=True)['exc'].agg(['size', 'mean', 'median']).reset_index()
            for t in (tous, blocs):
                t.insert(0, 'horizon', hor)
                t.insert(0, 'univers', u)
                lignes_q.append(t)
            # par annee, toutes societes de l'univers
            t = b[b.groupby('annee')['fcf_sur_ve'].transform('size') >= MIN_ANNEE].copy()
            t['quartile'] = t.groupby('annee')['fcf_sur_ve'].transform(quartile)
            m = t.groupby(['annee', 'quartile'], observed=True)['exc'].mean().unstack('quartile')
            md = t.groupby(['annee', 'quartile'], observed=True)['exc'].median().unstack('quartile')
            n = t.groupby('annee').size()
            a = pd.DataFrame({'univers': u, 'horizon': hor, 'annee': m.index, 'n': n.reindex(m.index).values,
                              'Q1_exc': m['Q1'].values, 'Q4_exc': m['Q4'].values, 'ecart_Q1_moins_Q4': (m['Q1'] - m['Q4']).values,
                              'ecart_mediane_Q1_moins_Q4': (md['Q1'] - md['Q4']).values})
            lignes_a.append(a)
    quartiles = pd.concat(lignes_q, ignore_index=True).rename(columns={'size': 'n', 'mean': 'exc_moyen', 'median': 'exc_median'})
    annees = pd.concat(lignes_a, ignore_index=True)
    return quartiles, annees


def t_newey_west(e, retards=2, annees=None):
    """t de la moyenne d'une serie annuelle, variance de Newey-West (poids de Bartlett) ; les rendements a 3 ans de depart voisins se recouvrent.
    Si `annees` est donne, le terme de retard k ne compte que les paires d'annees separees de k ans (une annee absente ne cree pas de fausse voisine)."""
    e = np.asarray(e, dtype=float)
    n = len(e)
    an = np.arange(n) if annees is None else np.asarray(annees)
    assert annees is None or np.all(np.diff(an) > 0), 'a14 : annees croissantes et uniques requises'
    if n <= retards + 1:
        return float('nan')
    c = e - e.mean()
    s = (c * c).sum() / n
    for k in range(1, retards + 1):
        s += 2 * (1 - k / (retards + 1)) * sum(c[i] * c[j] for i in range(n) for j in range(i + 1, n) if an[j] - an[i] == k) / n
    return e.mean() / np.sqrt(s / n)


def synthese_B(annees):
    out = []
    for (u, h), x in annees.groupby(['univers', 'horizon']):
        x = x.sort_values('annee')
        e = x['ecart_Q1_moins_Q4'].dropna()
        t = e.mean() / (e.std(ddof=1) / np.sqrt(len(e))) if len(e) > 2 else float('nan')
        serie = x.set_index('annee')['ecart_Q1_moins_Q4'].dropna()
        nw = t_newey_west(serie.values, annees=serie.index.values)
        nc = x[x['annee'].isin(ANNEES_NON_CHEVAUCHANTES)]['ecart_Q1_moins_Q4'].dropna()
        t_nc = nc.mean() / (nc.std(ddof=1) / np.sqrt(len(nc))) if (h == '3ans' and len(nc) > 2) else float('nan')
        out.append((u, h, len(e), int((e > 0).sum()), e.mean(), x['ecart_mediane_Q1_moins_Q4'].median(), t, nw, len(nc) if h == '3ans' else 0, t_nc))
    return pd.DataFrame(out, columns=['univers', 'horizon', 'annees', 'annees_Q1_gagne', 'ecart_moyen', 'ecart_mediane_mediane', 't_stat',
                                      't_newey_west', 'annees_non_chevauchantes', 't_non_chevauchant'])


def main():
    g, p, f, s = charger()
    d = construire_lignes(g, p, f, s)
    d.sort_values(['bloc', 'ticker', 'annee']).to_csv('backtest_lignes.csv', index=False)
    A = resume_A(d)
    A.to_csv('backtest_A_blocs.csv', index=False)
    Bq, Ba = resume_B(d)
    Bq.to_csv('backtest_B_quartiles.csv', index=False)
    Ba.to_csv('backtest_B_annees.csv', index=False)

    pd.set_option('display.width', 200)
    pd.set_option('display.float_format', lambda x: f'{x:.3f}')
    print('Lignes :', len(d), '| membres a la date :', int((d['univers'] == 'membres').sum()),
          '| avec test A :', d['g_reel'].notna().sum(), '| ret 1 an :', d['ret1'].notna().sum(), '| ret 3 ans :', d['ret3_ann'].notna().sum())
    print('\nTest A (g implicite contre croissance reelle du FCFF ; Standard : base N-1, 4 ans ; Cyclique : moyenne N-5..N-1, 6 ans) :')
    print(A.head(8).to_string(index=False))
    print('\nTest B (ecart de rendement en exces Q1 - Q4, moyenne sur les annees) :')
    print(synthese_B(Ba).to_string(index=False))


if __name__ == '__main__':
    main()
