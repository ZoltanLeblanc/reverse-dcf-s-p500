"""Table de correspondance ticker -> CIK de la SEC, avec gestion des changements de CIK.
Entree : un CSV (ticker_cik_sp500.csv) avec les colonnes ticker, cik et, pour les anciens CIK, cik_alternatif*/bascule_avant_date*.
Sortie : aucun fichier ; fournit une table en memoire.

Fonctions principales :
- charger_table_ticker_cik : lit le CSV et construit {ticker: CIK actuel + anciens CIK dates}.
- resoudre_cik : renvoie le CIK valable pour un ticker a une date donnee.
"""
import csv
from datetime import datetime

# paires de colonnes (cik ancien, date de bascule) du fichier csv
COLONNES_ALTERNATIFS = [
    ('cik_alternatif', 'bascule_avant_date'),
    ('cik_alternatif_2', 'bascule_avant_date_2'),
    ('cik_alternatif_3', 'bascule_avant_date_3'),
]

def charger_table_ticker_cik(chemin_csv):
    # construit {ticker: {'cik': cik_actuel, 'alternatifs': [(date_bascule, cik_ancien), ...]}}
    table = {}
    with open(chemin_csv, encoding='utf-8') as f:
        lecteur = csv.DictReader(f)
        for ligne in lecteur:
            ticker = ligne['ticker']
            # ticker abandonne (pas de cik) : on ne le met pas dans la table
            if ligne['cik'] == '':
                continue
            alternatifs = []
            for col_cik, col_date in COLONNES_ALTERNATIFS:
                cik_alt = ligne.get(col_cik, '')
                date_alt = ligne.get(col_date, '')
                if cik_alt != '' and date_alt != '':
                    date_bascule = datetime.strptime(date_alt, '%Y-%m-%d')
                    alternatifs.append((date_bascule, cik_alt))
            table[ticker] = {'cik': ligne['cik'], 'alternatifs': alternatifs}
    return table



def resoudre_cik(table, ticker, date_reference): 
    # renvoie le cik valable pour ce ticker a cette date (None si ticker absent de la table)
    if ticker not in table:
        return None

    entree = table[ticker]
    # on parcourt les bascules de la plus ancienne a la plus recente
    for date_bascule, cik_alt in sorted(entree['alternatifs']):
        if date_reference < date_bascule:
            return cik_alt

    return entree['cik']