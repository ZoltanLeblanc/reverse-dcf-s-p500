"""a15_controles.py : controles automatiques des donnees avant le calcul de g.
Lancer depuis ce dossier :  py a15_controles.py
1) saut du nombre d'actions (ajuste des splits) d'une annee a l'autre : x2,2 ou /2,2
2) capitalisation inferieure a 4 % du chiffre d'affaires
Les lignes deja traitees sont dans exclusions_manuelles.csv (exclues) ou controles_verifies.csv (verifiees, legitimes).
Il reste a examiner = lignes avec g calcule qui ne sont dans aucun des deux fichiers. Resultat : controles_a15.csv
Entrees : prix_cloture.csv, fondamentaux_sp500.csv, g_implicite.csv, exclusions_manuelles.csv, controles_verifies.csv.
Fonctions : lire_cles (ensemble de (cik, annee) d'un CSV), lire (CSV -> dictionnaire), nombre (texte -> nombre ou None).
"""

import csv

SAUT_HAUT, SAUT_BAS, CAP_CA_MIN = 2.2, 0.45, 0.04

def lire_cles(chemin):
    cles = set()
    fichier = open(chemin, 'r', encoding='utf-8-sig')
    for l in csv.DictReader(fichier):
        cles.add((str(int(l['cik'])), l['annee']))
    fichier.close()
    return cles

def lire(chemin, cle):
    table = {}
    fichier = open(chemin, 'r', encoding='utf-8-sig')
    for l in csv.DictReader(fichier):
        table[cle(l)] = l
    fichier.close()
    return table

def nombre(texte):
    return float(texte) if texte not in ('', None) else None

if __name__ == '__main__':
    exclues = lire_cles('exclusions_manuelles.csv')
    verifiees = lire_cles('controles_verifies.csv')
    prix = lire('prix_cloture.csv', lambda l: (str(int(l['cik'])), l['annee']))
    fond = lire('fondamentaux_sp500.csv', lambda l: (str(int(l['cik'])), l['annee']))
    g = lire('g_implicite.csv', lambda l: (str(int(l['cik'])), l['annee']))
    avec_g = {k for k, l in g.items() if l['g_implicite'] != ''}
    alertes = []
    for (cik, annee), l in prix.items():
        if l['statut'] != 'ok' or l['shares'] == '' or l['facteur_splits'] == '':
            continue
        actions = nombre(l['shares']) * nombre(l['facteur_splits'])
        avant = prix.get((cik, str(int(annee) - 1)))
        if (cik, str(int(annee) - 1)) in exclues:  # le saut vient d'une annee deja exclue (ex. FTI 2016) : pas d'alerte sur l'annee suivante
            avant = None
        if avant and avant['statut'] == 'ok' and avant['shares'] != '' and avant['facteur_splits'] != '':
            saut = actions / (nombre(avant['shares']) * nombre(avant['facteur_splits']))
            if saut > SAUT_HAUT or saut < SAUT_BAS:
                alertes.append((cik, l['ticker'], annee, 'saut actions', round(saut, 3)))
        ca = nombre(fond.get((cik, annee), {}).get('revenue', ''))
        cap = nombre(l['capitalisation'])
        if ca and cap and ca > 0 and cap / ca < CAP_CA_MIN:
            alertes.append((cik, l['ticker'], annee, 'capitalisation / CA', round(cap / ca, 3)))
    reste = [a for a in alertes if (a[0], a[2]) in avec_g and (a[0], a[2]) not in exclues and (a[0], a[2]) not in verifiees]
    deja = len(alertes) - len(reste)
    sortie = open('controles_a15.csv', 'w', newline='', encoding='utf-8')
    w = csv.writer(sortie)
    w.writerow(['cik', 'ticker', 'annee', 'controle', 'valeur'])
    w.writerows(reste)
    sortie.close()
    print(len(alertes), 'alertes,', deja, 'deja traitees (exclues ou verifiees),', len(reste), 'a examiner')
    for a in reste:
        print('  A EXAMINER :', a[1], a[2], a[3], a[4])
    print('Lignes exclues :', len(exclues), '. Si la liste est vide, les donnees passent les controles.')
