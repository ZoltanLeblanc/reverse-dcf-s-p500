"""Point d'entree : extrait les fondamentaux de tous les CIK de la table ticker -> CIK.
Entree : ticker_cik_sp500.csv. Sorties : fondamentaux_sp500.csv et alertes_fondamentaux.csv.
Fonctions principales (importees) :
- charger_table_ticker_cik : lit la table ticker -> CIK.
- construire_liste_cik_a_traiter : liste triee des CIK uniques.
- ecrire_fondamentaux : ecrit les fondamentaux par CIK et par annee, et les alertes."""
from a01_ticker_CIK import charger_table_ticker_cik 
from a02_main import construire_liste_cik_a_traiter
from a05_fundamental_extraction import ecrire_fondamentaux

if __name__ == '__main__':
    table = charger_table_ticker_cik('ticker_cik_sp500.csv') # Lit la table ticker -> CIK (avec les CIK alternatifs)
    liste_ciks = construire_liste_cik_a_traiter(table) # Liste triee de tous les CIK uniques a traiter
    nb = ecrire_fondamentaux(liste_ciks, 'fondamentaux_sp500.csv', 'alertes_fondamentaux.csv') # Ecrit un tableau par CIK et par annee, et un fichier d'alertes
    print('termine : ' + str(nb) + ' entreprises ecrites sur ' + str(len(liste_ciks)))