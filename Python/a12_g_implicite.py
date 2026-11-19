"""a12 - g implicite par la methode du reverse DCF (une seule phase), avec un WACC de marche par annee.

Usage en ligne de commande :
  py a12_g_implicite.py                  -> WACC de marche (prime 5 %, ecart de credit 1,5 pt), ecrit g_implicite.csv
  py a12_g_implicite.py fixe             -> ancien r fixe (9 % Standard / 10 % Cyclique), ecrit g_implicite_fixe.csv
  py a12_g_implicite.py wacc 0.04 0.02   -> autre prime de risque / ecart de credit

FCFF = OCF + interets x (1 - T) - capex  (T = 35 % jusqu'en 2017, 21 % ensuite ; interets absents = 0)
WACC = E/V x (DGS10 + prime) + D/V x (DGS10 + ecart) x (1 - T), cycliques + 1 point
DGS10 = dernier taux connu a la date de cloture de la ligne (jamais posterieur). E/V, D/V = sommes de l'annee ;
2026 (peu de lignes) reprend la structure de 2025. Seules les societes Standard et Cyclique de cik_categorie.csv ont un g.

Entrees : valeur_entreprise.csv, fondamentaux_sp500.csv, cik_categorie.csv, prix_cloture.csv, dgs10_fred.csv, exclusions_manuelles.csv.
Fonctions principales : lire_exclusions, charger_taux / dernier_taux (taux a 10 ans), structure_par_annee (E/V, D/V),
wacc, calculer_fcf / fcf_retenu (FCFF de l'annee, ou moyenne lissee pour les cycliques), ecrire_g (ecrit le CSV de g).
"""

import bisect
import csv
import sys

TAUX_R = {'Standard': 0.09, 'Cyclique': 0.10}  # ancien r fixe, utilise en mode `fixe`
PRIME_RISQUE = 0.05
ECART_CREDIT = 0.015
SURPLUS_CYCLIQUE = 0.01
ANNEES_LISSAGE_CYCLIQUE = 5     # Cyclique : FCF moyen sur 5 ans au lieu de l'annee
FCF_MIN_RELATIF = 0.01          # FCF / valeur d'entreprise minimum : en dessous, g n'a pas de sens
FICHIER_TAUX = 'dgs10_fred.csv' # cache de la serie FRED DGS10 : colonnes date, taux_10_ans_pct
ANNEE_STRUCTURE_REPRISE = 2026  # annee dont la structure E/V, D/V est remplacee par celle de l'annee precedente


def lire_exclusions(chemin='exclusions_manuelles.csv'): # lignes (cik, annee) a ne pas utiliser, avec la raison
    ensemble = set()
    fichier = open(chemin, 'r', encoding='utf-8-sig')
    for ligne in csv.DictReader(fichier):
        ensemble.add((str(int(ligne['cik'])), ligne['annee']))
    fichier.close()
    return ensemble

def lire(chemin):
    table = {}
    fichier = open(chemin, 'r', encoding='utf-8-sig')
    for ligne in csv.DictReader(fichier):
        table[(str(int(ligne['cik'])), ligne['annee'])] = ligne
    fichier.close()
    return table

def categories_cik(chemin='cik_categorie.csv'): # categorie de chaque CIK (la source de verite, y compris les corrections manuelles)
    return {str(int(l['cik'])): l['categorie'] for l in csv.DictReader(open(chemin, encoding='utf-8-sig'))}

def impot(annee):
    return 0.35 if annee <= 2017 else 0.21

def charger_taux(chemin=FICHIER_TAUX):
    dates, taux = [], []
    for ligne in csv.DictReader(open(chemin, encoding='utf-8-sig')):
        dates.append(ligne['date'])
        taux.append(float(ligne['taux_10_ans_pct']) / 100)
    return dates, taux

def dernier_taux(serie, jour): # dernier taux connu a la date `jour` (YYYY-MM-DD), jamais posterieur
    dates, taux = serie
    i = bisect.bisect_right(dates, jour) - 1
    return taux[i] if i >= 0 else None

def structure_par_annee(ve): # E/V et D/V : sommes des capitalisations et des dettes brutes (lignes qui ont les deux)
    cap, dette = {}, {}
    for (cik, annee), l in ve.items():
        if l['capitalisation'] == '' or l['dette'] == '':
            continue
        a = int(annee)
        cap[a] = cap.get(a, 0.0) + float(l['capitalisation'])
        dette[a] = dette.get(a, 0.0) + float(l['dette'])
    s = {a: (cap[a] / (cap[a] + dette[a]), dette[a] / (cap[a] + dette[a])) for a in cap}
    if ANNEE_STRUCTURE_REPRISE in s and ANNEE_STRUCTURE_REPRISE - 1 in s:
        s[ANNEE_STRUCTURE_REPRISE] = s[ANNEE_STRUCTURE_REPRISE - 1]
    return s

def wacc(taux10, ev, dv, annee, prime=PRIME_RISQUE, ecart=ECART_CREDIT):
    return ev * (taux10 + prime) + dv * (taux10 + ecart) * (1 - impot(annee))

def dates_cloture(chemin='prix_cloture.csv'):
    d = {}
    for l in csv.DictReader(open(chemin, encoding='utf-8-sig')):
        if l['date_cloture']:
            d[(str(int(l['cik'])), l['annee'])] = l['date_cloture']
    return d

def _nombre(ligne, nom):
    return float(ligne[nom]) if ligne is not None and ligne[nom] != '' else None

def calculer_fcf(fond, cik, annee): # FCFF = OCF + interets x (1 - T) - capex, ou None
    ligne = fond.get((cik, str(annee)))
    ocf, capex = _nombre(ligne, 'ocf'), _nombre(ligne, 'capex')
    if ocf is None or capex is None:
        return None
    interet = _nombre(ligne, 'interest') or 0.0
    return ocf + abs(interet) * (1 - impot(annee)) - capex

def fcf_retenu(fond, cik, annee, categorie, exclues=()): # Standard : FCFF de l'annee. Cyclique : moyenne des dernieres annees (hors annees exclues, comme a14)
    if categorie != 'Cyclique':
        return calculer_fcf(fond, cik, annee)
    valeurs = []
    for a in range(annee - ANNEES_LISSAGE_CYCLIQUE + 1, annee + 1):
        if (cik, str(a)) in exclues: # un FCFF exclu pour donnee fausse n'entre pas dans la moyenne
            continue
        v = calculer_fcf(fond, cik, a)
        if v is not None:
            valeurs.append(v)
    if len(valeurs) < 3: # Pas assez d'historique pour lisser
        return None
    return sum(valeurs) / len(valeurs)

def ecrire_g(mode='wacc', prime=PRIME_RISQUE, ecart=ECART_CREDIT, chemin_ve='valeur_entreprise.csv',
             chemin_fond='fondamentaux_sp500.csv', chemin_sortie=None):
    exclusions = lire_exclusions()  # lu ici et non a l'import : a14 importe ce module sans etre toujours lance depuis Python
    ve = lire(chemin_ve)
    fond = lire(chemin_fond)
    cats = categories_cik()
    serie = charger_taux()
    structure = structure_par_annee(ve)
    clotures = dates_cloture()
    if chemin_sortie is None:
        chemin_sortie = 'g_implicite.csv' if mode == 'wacc' else 'g_implicite_fixe.csv'
    sortie = open(chemin_sortie, 'w', newline='', encoding='utf-8')
    ecrivain = csv.writer(sortie)
    ecrivain.writerow(['cik', 'annee', 'ticker', 'categorie', 'valeur_entreprise', 'fcf', 'taux_10_ans', 'r', 'g_implicite', 'statut'])
    for (cik, annee) in ve:
        ligne = ve[(cik, annee)]
        categorie = cats.get(cik, ligne['categorie'])
        if categorie not in TAUX_R: # seules les societes Standard et Cyclique ont un g (AMP, banques, assurances... exclues)
            continue
        if ligne['valeur_entreprise'] == '':
            raise SystemExit(f'a12 : valeur_entreprise vide pour cik {cik}, annee {annee} (dette ou tresorerie manquante dans a11)')
        valeur = float(ligne['valeur_entreprise'])
        t10 = dernier_taux(serie, clotures.get((cik, annee), annee + '-12-31'))
        if mode == 'fixe':
            r = TAUX_R[categorie]
        else:
            ev, dv = structure[int(annee)]
            r = wacc(t10, ev, dv, int(annee), prime, ecart) + (SURPLUS_CYCLIQUE if categorie == 'Cyclique' else 0.0)
        fcf = fcf_retenu(fond, cik, int(annee), categorie, exclusions)
        g = ''
        if (cik, annee) in exclusions:
            statut = 'exclu'
        elif valeur <= 0:
            statut = 'VE negative'
        elif fcf is None:
            statut = 'fcf indisponible'
        elif fcf <= 0 or fcf / valeur < FCF_MIN_RELATIF:
            statut = 'fcf trop faible'
        else:
            g = (valeur * r - fcf) / (valeur + fcf)
            statut = 'ok'
        ecrivain.writerow([cik, annee, ligne['ticker'], categorie, valeur, fcf if fcf is not None else '',
                           t10 if t10 is not None else '', r, g, statut])
    sortie.close()
    return chemin_sortie

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'wacc'
    prime = float(sys.argv[2]) if len(sys.argv) > 2 else PRIME_RISQUE
    ecart = float(sys.argv[3]) if len(sys.argv) > 3 else ECART_CREDIT
    print('ecrit :', ecrire_g(mode, prime, ecart))
