"""Point d'entree du telechargement des donnees companyfacts de la SEC.
Entree : ticker_cik_sp500.csv (via a01_ticker_CIK).
Sortie : fichiers JSON mis en cache dans le dossier Companyfacts (via a03_sec_api).

Fonctions principales :
- construire_liste_cik_a_traiter : rassemble les CIK uniques (actuels et anciens) a recuperer.
- lancer_recuperation_pour_tous : telecharge les donnees de chaque CIK et affiche la progression.
"""
from a01_ticker_CIK import charger_table_ticker_cik
from a03_sec_api import obtenir_donnees_entreprise

def construire_liste_cik_a_traiter(table_ticker_cik): # Rassemble tous les CIK uniques a recuperer
    ciks_a_traiter = set()

    for ticker in table_ticker_cik:
        entree = table_ticker_cik[ticker]
        ciks_a_traiter.add(entree['cik'])

        for date_bascule, cik_alt in entree['alternatifs']:
            ciks_a_traiter.add(cik_alt)

    return sorted(ciks_a_traiter)

def lancer_recuperation_pour_tous(chemin_table_ticker_cik):
    table_ticker_cik = charger_table_ticker_cik(chemin_table_ticker_cik)
    ciks_a_traiter = construire_liste_cik_a_traiter(table_ticker_cik)

    nombre_total = len(ciks_a_traiter)
    compteur = 0

    for cik in ciks_a_traiter:
            compteur = compteur + 1
            print('traitement ' + str(compteur) + ' / ' + str(nombre_total) + ' : CIK ' + cik)
            donnees = obtenir_donnees_entreprise(cik)

            if donnees is None:
                print('cik ignore, pas de donnees : ' + cik)
                continue

if __name__ == '__main__':
    lancer_recuperation_pour_tous('ticker_cik_sp500.csv')