"""a13 - Classement des societes en blocs sectoriels a partir du code SIC.

Entrees : cik_categorie.csv (categorie, SIC), secteur_manuel.csv (blocs fixes a la main : cik, bloc, raison).
Sortie : secteur.csv (une ligne par societe Standard ou Cyclique : bloc et source du classement).

Fonctions principales :
 - lire_manuel : charge les classements manuels.
 - bloc_depuis_sic : donne le bloc d'un code SIC selon REGLES_BLOCS.
 - ecrire_secteurs : ecrit secteur.csv et renvoie le nombre de societes par bloc.
"""

import csv

CATEGORIES_CIBLES = ['Standard', 'Cyclique']

# Blocs et plages de SIC : la premiere plage qui correspond gagne. Le fichier secteur_manuel.csv prime sur ces regles.
REGLES_BLOCS = [
    ('Logiciels et services IT', [(7370, 7379)]),
    ('Materiel tech et semi-conducteurs', [(3570, 3579), (3660, 3679), (5065, 5065)]),
    ('Sante', [(2830, 2836), (3820, 3829), (3840, 3859), (5047, 5047), (5122, 5122), (6324, 6324), (8000, 8099)]),
    ('Conso de base', [(100, 199), (2000, 2199), (2840, 2844), (5140, 5199), (5400, 5499), (5900, 5999)]),
    ('Conso discretionnaire', [(2200, 2399), (2510, 2599), (3010, 3199), (3630, 3639), (3711, 3716), (3750, 3799),
                               (3650, 3659), (3860, 3879), (3942, 3949), (5200, 5399), (5500, 5899), (7000, 7099), (7200, 7299), (7500, 7599),
                               (7900, 7999), (8200, 8299)]),
    ('Industrie et transport', [(1500, 1799), (3400, 3569), (3580, 3629), (3640, 3649), (3680, 3699), (3710, 3710), (3720, 3749), (3800, 3819),
                                (3990, 3990), (4000, 4799), (4953, 4955), (5000, 5099), (5110, 5110), (7300, 7399), (8700, 8799)]),
    ('Matieres et energie', [(1000, 1499), (2400, 2499), (2600, 2699), (2800, 2829), (2850, 2899), (2900, 2999),
                             (3200, 3299), (3310, 3390), (4900, 4952), (4990, 4999), (6792, 6792)]),
    ('Telecom et medias', [(2700, 2799), (4800, 4899), (7810, 7849)]),
    ('Finance non bancaire et paiements', [(6200, 6299), (6400, 6599)]),
]

def lire_manuel(chemin): # Lit secteur_manuel.csv : cik,bloc,raison
    table = {}
    fichier = open(chemin, 'r', encoding='utf-8-sig')
    for ligne in csv.DictReader(fichier):
        table[str(int(ligne['cik']))] = (ligne['bloc'].strip(), ligne['raison'].strip())
    fichier.close()
    return table

def bloc_depuis_sic(sic_texte): # Renvoie le bloc d'un code SIC, ou '' si aucune regle ne correspond
    if sic_texte.strip() == '':
        return ''
    sic = int(float(sic_texte))
    for bloc, plages in REGLES_BLOCS:
        for sic_min, sic_max in plages:
            if sic_min <= sic <= sic_max:
                return bloc
    return ''

def ecrire_secteurs(chemin_categories, chemin_manuel, chemin_sortie):
    manuel = lire_manuel(chemin_manuel)
    sortie = open(chemin_sortie, 'w', newline='', encoding='utf-8')
    ecrivain = csv.writer(sortie)
    ecrivain.writerow(['cik', 'ticker', 'sic', 'sic_description', 'categorie', 'bloc', 'source'])
    comptes = {}
    fichier = open(chemin_categories, 'r', encoding='utf-8-sig')
    for ligne in csv.DictReader(fichier):
        cik = str(int(ligne['cik']))
        if ligne['categorie'] not in CATEGORIES_CIBLES:
            continue
        if cik in manuel:
            bloc, source = manuel[cik][0], 'manuel : ' + manuel[cik][1]
        else:
            bloc = bloc_depuis_sic(ligne['sic'])
            source = 'sic' if bloc != '' else 'a classer'
        if bloc == '':
            bloc = 'A CLASSER'
        ecrivain.writerow([cik, ligne['ticker'], ligne['sic'], ligne['sic_description'], ligne['categorie'], bloc, source])
        comptes[bloc] = comptes.get(bloc, 0) + 1
    fichier.close()
    sortie.close()
    return comptes

if __name__ == '__main__':
    comptes = ecrire_secteurs('cik_categorie.csv', 'secteur_manuel.csv', 'secteur.csv')
    for bloc in sorted(comptes, key=comptes.get, reverse=True):
        print(str(comptes[bloc]) + ' : ' + bloc)
