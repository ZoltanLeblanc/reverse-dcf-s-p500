"""a11 - Valeur d'entreprise (VE) et multiples, ligne par ligne.

Entrees : prix_cloture.csv (capitalisation), fondamentaux_sp500.csv (dette, tresorerie, chiffre d'affaires, EBIT).
Sortie : valeur_entreprise.csv (VE = capitalisation + dette - tresorerie ; ev_revenue ; ev_ebit).

Fonctions principales :
 - lire : charge un CSV dans un dictionnaire {(cik, annee): ligne}.
 - nombre : convertit un texte en nombre (texte vide -> None).
 - ecrire_valeur_entreprise : calcule et ecrit la VE et les multiples pour les lignes au prix valide.
"""

import csv

def lire(chemin): # Renvoie un dictionnaire {(cik, annee): ligne}
    table = {}
    fichier = open(chemin, 'r', encoding='utf-8-sig')
    for ligne in csv.DictReader(fichier):
        table[(str(int(ligne['cik'])), ligne['annee'])] = ligne
    fichier.close()
    return table

def nombre(texte): # Texte vide -> None, sinon le nombre
    if texte == '':
        return None
    return float(texte)

def ecrire_valeur_entreprise(chemin_prix, chemin_fondamentaux, chemin_sortie):
    prix = lire(chemin_prix)
    fond = lire(chemin_fondamentaux)
    sortie = open(chemin_sortie, 'w', newline='', encoding='utf-8')
    ecrivain = csv.writer(sortie)
    ecrivain.writerow(['cik', 'annee', 'ticker', 'categorie', 'capitalisation', 'dette', 'cash',
                       'valeur_entreprise', 'ev_revenue', 'ev_ebit'])
    for cle in prix:
        p = prix[cle]
        f = fond.get(cle)
        if f is None:
            raise SystemExit(f'a11 : fondamentaux absents pour (cik, annee) = {cle}')
        if p['statut'] != 'ok': # Seules les lignes avec un prix valide
            continue
        cap = nombre(p['capitalisation'])
        dette_lt = nombre(f['long_term_debt'])
        dette_ct = nombre(f['current_debt'])
        cash = nombre(f['cash'])
        revenue = nombre(f['revenue'])
        ebit = nombre(f['ebit'])
        dette = None
        valeur = None
        if dette_lt is not None and dette_ct is not None:
            dette = dette_lt + dette_ct
        if cap is not None and dette is not None and cash is not None:
            valeur = cap + dette - cash
        ev_revenue = ''
        ev_ebit = ''
        if valeur is not None and revenue:
            ev_revenue = valeur / revenue
        if valeur is not None and ebit and ebit > 0:
            ev_ebit = valeur / ebit
        ecrivain.writerow([p['cik'], p['annee'], p['ticker'], p['categorie'],
                           p['capitalisation'], dette if dette is not None else '',
                           cash if cash is not None else '',
                           valeur if valeur is not None else '', ev_revenue, ev_ebit])
    sortie.close()

if __name__ == '__main__':
    ecrire_valeur_entreprise('prix_cloture.csv', 'fondamentaux_sp500.csv', 'valeur_entreprise.csv')