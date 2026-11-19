"""Classification par CIK : chaque CIK du fichier des fondamentaux recoit sa propre categorie, sans passer par le ticker.
Ordre de decision : 1) correction manuelle (classification_manuelle.csv), 2) SIC propre au CIK (cache ou SEC),
3) SIC du ticker actuel si le CIK est un ancien CIK que la SEC ne renseigne pas, 4) 'Non applicable' si rien.
Entrees : fondamentaux_sp500.csv, ticker_cik_sp500.csv, classification_manuelle.csv, SIC en cache ou via la SEC.
Sortie : cik_categorie.csv.
Fonctions principales :
- lire_ciks_fondamentaux : liste triee des CIK presents dans les fondamentaux.
- construire_ticker_par_cik : ticker et CIK actuel associes a chaque CIK.
- charger_classification_manuelle : corrections manuelles cik -> categorie.
- classer_ciks : applique l'ordre de decision ci-dessus a chaque CIK.
- ecrire_classification_cik : enchaine les etapes et ecrit cik_categorie.csv."""
import csv
import os
from a01_ticker_CIK import charger_table_ticker_cik
from a09_sec_sic import obtenir_sic_entreprise
from a08_classification import categorie_depuis_sic, lire_sic


def lire_ciks_fondamentaux(chemin_fondamentaux): # Liste triee des CIK presents dans fondamentaux_sp500.csv
    ciks = set()
    fichier = open(chemin_fondamentaux, 'r', encoding='utf-8-sig')
    lecteur = csv.DictReader(fichier)
    for ligne in lecteur:
        ciks.add(str(int(ligne['cik'])))
    fichier.close()
    return sorted(ciks, key=int)

def construire_ticker_par_cik(table): # {cik: (ticker, cik_actuel_du_ticker)} : pour un ancien CIK, renvoie le ticker et le CIK actuel de ce ticker
    resultat = {}
    for ticker in sorted(table):
        cik_actuel = str(int(table[ticker]['cik']))
        if cik_actuel not in resultat:
            resultat[cik_actuel] = (ticker, cik_actuel)
    for ticker in sorted(table):
        cik_actuel = str(int(table[ticker]['cik']))
        for date_bascule, cik_alt in table[ticker]['alternatifs']:
            cle = str(int(cik_alt))
            if cle not in resultat:
                resultat[cle] = (ticker, cik_actuel)
    return resultat

def charger_classification_manuelle(chemin): # Lit classification_manuelle.csv : cik,categorie,raison
    table = {}
    if not os.path.exists(chemin):
        return table
    fichier = open(chemin, 'r', encoding='utf-8-sig')
    lecteur = csv.DictReader(fichier)
    for ligne in lecteur:
        table[str(int(ligne['cik']))] = (ligne['categorie'].strip(), ligne['raison'].strip())
    fichier.close()
    return table

def classer_ciks(liste_ciks, ticker_par_cik, manuelle, lire_sic_cik): # Renvoie une liste de lignes [cik, ticker, sic, description, categorie, source, a_verifier]
    lignes = []
    compteur = 0
    for cik in liste_ciks:
        compteur = compteur + 1
        ticker = ''
        if cik in ticker_par_cik:
            ticker = ticker_par_cik[cik][0]
        resultat = lire_sic_cik(cik)
        sic = None
        description = ''
        origine = 'sic du cik'
        if resultat is not None:
            sic = lire_sic(resultat['sic'])
            description = resultat['description']
        if sic is None and cik in ticker_par_cik and ticker_par_cik[cik][1] != cik: # Ancien CIK sans SIC : on prend celui du CIK actuel du ticker
            resultat = lire_sic_cik(ticker_par_cik[cik][1])
            if resultat is not None:
                sic = lire_sic(resultat['sic'])
                description = resultat['description']
                origine = 'sic du ticker actuel'
        categorie, a_verifier, source = categorie_depuis_sic(sic)
        if source == 'regle sic' or source == 'defaut':
            source = origine + ' (' + source + ')'
        if cik in manuelle:
            categorie = manuelle[cik][0]
            source = 'manuelle : ' + manuelle[cik][1]
            a_verifier = 'non'
        lignes.append([cik, ticker, '' if sic is None else sic, description, categorie, source, a_verifier])
        print(str(compteur) + '/' + str(len(liste_ciks)) + ' : CIK ' + cik + ' ' + ticker + ' -> ' + categorie)
    return lignes

def ecrire_classification_cik(chemin_fondamentaux, chemin_table_cik, chemin_manuelle, chemin_sortie): # Ecrit cik_categorie.csv
    table = charger_table_ticker_cik(chemin_table_cik)
    liste_ciks = lire_ciks_fondamentaux(chemin_fondamentaux)
    ticker_par_cik = construire_ticker_par_cik(table)
    manuelle = charger_classification_manuelle(chemin_manuelle)
    lignes = classer_ciks(liste_ciks, ticker_par_cik, manuelle, obtenir_sic_entreprise)
    sortie = open(chemin_sortie + '.tmp', 'w', newline='', encoding='utf-8')
    ecrivain = csv.writer(sortie)
    ecrivain.writerow(['cik', 'ticker', 'sic', 'sic_description', 'categorie', 'source', 'a_verifier'])
    for ligne in lignes:
        ecrivain.writerow(ligne)
    sortie.close()
    os.replace(chemin_sortie + '.tmp', chemin_sortie)
    return len(lignes)

if __name__ == '__main__':
    nb = ecrire_classification_cik('fondamentaux_sp500.csv', 'ticker_cik_sp500.csv', 'classification_manuelle.csv', 'cik_categorie.csv')
    print('termine : ' + str(nb) + ' CIK classes')
