"""Extraction des fondamentaux annuels a partir des JSON companyfacts de la SEC.
Entrees : fichiers JSON du dossier de cache (a03_sec_api), tags de a04_tags, dette_manuelle.csv.
Sorties : le CSV des fondamentaux annuels par entreprise et le CSV d'alertes (chemins passes en argument).

Fonctions principales :
- extraire_historique_annuel : historique annuel d'un tag (valeurs des 10-K, duree et cloture controlees).
- extraire_avec_candidats / extraire_dette / extraire_revenue / extraire_da / extraire_capex : choix de la valeur par metrique selon la priorite des tags et des gardes-fous.
- extraire_actions : nombre d'actions nettoye (echelle corrigee) avec replis.
- extraire_cash_v3 : tresorerie plus placements court et long terme.
- extraire_toutes_metriques : regroupe toutes les metriques par annee.
- construire_lignes_annuelles : une ligne par annee (EBIT, dette, interets reconstitues si besoin).
- controler_lignes : alertes de coherence ; ecrire_fondamentaux : ecrit les deux CSV.
"""
import os
import csv
import json
from datetime import date, timedelta 
from a03_sec_api import DOSSIER_CACHE

from a04_tags import MIN_DURATION_DAYS
from a04_tags import TAGS_CAPEX_DERNIER_RECOURS
from a04_tags import TAGS_CAPEX_PETROLE
from a04_tags import TAGS_LT_SECURITIES
from a04_tags import MAX_DURATION_DAYS

from a04_tags  import TAGS_REVENUE 
from a04_tags  import TAGS_EBIT 
from a04_tags  import TAGS_DEPRECIATION_AMORTIZATION 
from a04_tags  import TAGS_DA_SECOURS
from a04_tags  import TAGS_INCOME_TAX 
from a04_tags  import TAGS_INTEREST_EXPENSE
from a04_tags  import TAGS_OCF
from a04_tags  import TAGS_CAPEX 
from a04_tags  import TAGS_CASH 
from a04_tags  import TAGS_ST_INVEST 
from a04_tags  import TAGS_LONG_TERM_DEBT 
from a04_tags  import TAGS_CURRENT_DEBT 
from a04_tags  import TAGS_SHARES_OUTSTANDING
from a04_tags  import TAGS_PRETAX_INCOME

TAGS_FIN_EXERCICE = ['NetCashProvidedByUsedInOperatingActivities', 'NetIncomeLoss', 'ProfitLoss', 'Revenues', 'OperatingIncomeLoss', 'IncomeTaxExpenseBenefit'] # Servent a reperer les vraies dates de cloture d'exercice

def trouver_fins_exercice(donnees): # Ensemble des dates de fin des exercices complets declares dans les 10-K
    fins = set()
    facts_us_gaap = donnees.get('facts', {}).get('us-gaap', {})
    for nom_tag in TAGS_FIN_EXERCICE:
        if nom_tag in facts_us_gaap:
            for entree in facts_us_gaap[nom_tag].get('units', {}).get('USD', []):
                if entree.get('form', '') == '10-K' and entree.get('start') is not None:
                    duree = (date.fromisoformat(entree.get('end')) - date.fromisoformat(entree.get('start'))).days
                    if duree >= MIN_DURATION_DAYS and duree <= MAX_DURATION_DAYS:
                        fins.add(date.fromisoformat(entree.get('end')))
    return fins

def est_proche_fin_exercice(fin_texte, fins): # Vrai si la date est a moins de 10 jours d'une cloture d'exercice (ou si aucune cloture n'est connue)
    if len(fins) == 0:
        return True
    fin = date.fromisoformat(fin_texte)
    for cloture in fins:
        if abs((fin - cloture).days) <= 10:
            return True
    return False

def extraire_historique_annuel(donnees, nom_tag, unite='USD'): # Recupere l'historique annuel d'un concept comptable, unite = 'USD' ou 'shares'
    resultat = {}
    dates_depot = {} # annee -> date de depot de la valeur retenue
    dates_fin = {} # annee -> date de fin de la valeur retenue

    facts_us_gaap = donnees.get('facts', {}).get('us-gaap', {}) # On se place dans la taxonomie us-gaap du json companyfacts

    if nom_tag not in facts_us_gaap: # Cette entreprise n'a jamais declare ce tag
        return resultat

    unites = facts_us_gaap[nom_tag].get('units', {}) # Les valeurs sont rangees par unite (USD, shares, etc.)
    if '_fins_exercice' not in donnees: # Calcule une seule fois par entreprise
        donnees['_fins_exercice'] = trouver_fins_exercice(donnees)
    fins_exercice = donnees['_fins_exercice']

    if unite not in unites: # Le tag existe mais pas dans l'unite demandee
        return resultat

    for entree in unites[unite]: # Chaque entree correspond a une valeur declaree dans un depot precis
        formulaire = entree.get('form', '') # Type de depot : 10-K (annuel), 10-Q (trimestriel), etc.
        periode_fiscale = entree.get('fp', '') # FY = annee fiscale complete

        if formulaire == '10-K' and periode_fiscale in ['FY', 'Q4']: # Certains exercices decales sont etiquetes Q4 dans le 10-K
            debut_texte = entree.get('start') # Les concepts de flux ont une date de debut, pas les concepts de bilan
            if debut_texte is None and not est_proche_fin_exercice(entree.get('end'), fins_exercice): # Valeur de bilan datee hors cloture d'exercice (trimestre) : ecartee
                continue
            if debut_texte is not None:
                duree = (date.fromisoformat(entree.get('end')) - date.fromisoformat(debut_texte)).days
                if duree < MIN_DURATION_DAYS or duree > MAX_DURATION_DAYS: # On ecarte les trimestres presents dans le 10-K
                    continue

            annee = (date.fromisoformat(entree.get('end')) - timedelta(days=15)).year # evite les collisions des exercices de 52/53 semaines
            depot = entree.get('filed', '')
            fin = entree.get('end')
            if annee not in resultat or depot < dates_depot[annee] or (depot == dates_depot[annee] and fin > dates_fin[annee]): # depot le plus ancien ; a depot egal, la date de fin la plus tardive
                resultat[annee] = entree.get('val')
                dates_depot[annee] = depot
                dates_fin[annee] = fin

    donnees.setdefault('_depots', {})[nom_tag] = dates_depot # date de depot de la valeur retenue, par annee (sert a dater le depart du test B)
    return resultat

def extraire_avec_candidats(donnees, liste_tags_candidats, unite='USD'): 
    resultat_fusionne = {}

    for nom_tag in liste_tags_candidats: # On parcourt les tags dans l'ordre de priorite
        historique_tag = extraire_historique_annuel(donnees, nom_tag, unite)

        for annee in historique_tag:
            if annee not in resultat_fusionne: # On ne remplit que les annees pas encore couvertes par un tag precedent
                resultat_fusionne[annee] = historique_tag[annee]

    return resultat_fusionne

def extraire_dette(donnees, tags): # Comme extraire_avec_candidats, mais un 0 publie ne masque pas un tag suivant non nul
    resultat = {}
    annees_zero = []
    for nom_tag in tags:
        historique_tag = extraire_historique_annuel(donnees, nom_tag)
        for annee in historique_tag:
            valeur = abs(historique_tag[annee]) # Une dette n'est jamais negative : certains premiers depots ont le mauvais signe
            if valeur != 0:
                if annee not in resultat:
                    resultat[annee] = valeur
            else:
                annees_zero.append(annee)
    for annee in annees_zero: # Un zero n'est retenu que si aucun tag ne donne une dette non nulle cette annee
        if annee not in resultat:
            resultat[annee] = 0
    return resultat

SEUIL_REVENUE = 0.5 # Une valeur inferieure a la moitie de la plus grande de l'annee est ecartee (valeur parasite ou composant)
def extraire_revenue(donnees): # Garde l'ordre de priorite des tags, mais ecarte les valeurs nulles ou trop petites
    valeurs_par_annee = {} # annee -> liste des valeurs, dans l'ordre de priorite des tags

    for nom_tag in TAGS_REVENUE:
        historique_tag = extraire_historique_annuel(donnees, nom_tag)

        for annee in historique_tag:
            if annee not in valeurs_par_annee:
                valeurs_par_annee[annee] = []
            valeurs_par_annee[annee].append(historique_tag[annee])

    resultat = {}
    for annee in valeurs_par_annee:
        valeurs = valeurs_par_annee[annee]
        plus_grande = max(valeurs)

        for valeur in valeurs:
            if valeur > 0 and valeur >= SEUIL_REVENUE * plus_grande: # Premiere valeur correcte dans l'ordre de priorite
                resultat[annee] = valeur
                break

        if annee not in resultat: # Aucune valeur positive (ex : revenue negatif reel) : on garde la premiere
            resultat[annee] = valeurs[0]

    return resultat

SEUIL_DA = 0.5 # Un total de D&A plus petit que la moitie du plus grand candidat de l'annee est un composant ou une valeur parasite
SEUIL_INTERETS_DETTE_NULLE = 5000000 # Une dette a 0 avec plus de 5 M d'interets est consideree comme non lue (dette inconnue)
TAUX_INTERET_MAX = 0.30 # Des interets superieurs a 30 % de la dette lue montrent que la dette est incomplete (taux typique 4,5 %, 95 % des lignes sous 10 %)
TAUX_DETTE_IMPLICITE = 0.05 # Taux moyen suppose pour estimer la dette que les interets laissent supposer (taux typique 4,5 %)
RATIO_MATERIALITE = 0.25 # Une dette manquante inferieure a 25 % du cash flow operationnel est negligeable pour la valeur d'entreprise : la dette n'est pas declaree inconnue

def extraire_da(donnees): # D&A : on rassemble les candidats de l'annee, puis on ecarte ceux qui sont trop petits face au plus grand
    candidats = {} # annee -> liste de valeurs, dans l'ordre de priorite
    for nom_tag in TAGS_DEPRECIATION_AMORTIZATION[:3]:
        historique_tag = extraire_historique_annuel(donnees, nom_tag)
        for annee in historique_tag:
            if annee not in candidats:
                candidats[annee] = []
            candidats[annee].append(abs(historique_tag[annee]))

    depreciation = extraire_historique_annuel(donnees, 'Depreciation')
    amortissement = extraire_historique_annuel(donnees, 'AmortizationOfIntangibleAssets')
    for annee in depreciation:
        if annee not in candidats:
            candidats[annee] = []
        if annee in amortissement:
            candidats[annee].append(abs(depreciation[annee]) + abs(amortissement[annee]))
        else:
            candidats[annee].append(abs(depreciation[annee]))

    resultat = {}
    for annee in candidats:
        valeurs = candidats[annee]
        plus_grande = max(valeurs)
        for valeur in valeurs:
            if valeur >= SEUIL_DA * plus_grande: # Premiere valeur correcte dans l'ordre de priorite
                resultat[annee] = valeur
                break

    for nom_tag in TAGS_DA_SECOURS: # Dernier recours : seulement les annees sans aucun candidat
        historique_tag = extraire_historique_annuel(donnees, nom_tag)
        for annee in historique_tag:
            if annee not in resultat:
                resultat[annee] = abs(historique_tag[annee])

    for annee in list(resultat.keys()): # Chute isolee : un petit total entre deux annees beaucoup plus grandes est remplace par un poste de D&A plus grand de la meme annee
        if annee - 1 in resultat and annee + 1 in resultat:
            if resultat[annee - 1] > 5 * resultat[annee] and resultat[annee + 1] > 5 * resultat[annee]:
                meilleur = resultat[annee]
                for nom_tag in TAGS_DA_SECOURS:
                    historique_tag = extraire_historique_annuel(donnees, nom_tag)
                    if annee in historique_tag and abs(historique_tag[annee]) > 2 * meilleur and abs(historique_tag[annee]) > 2 * resultat[annee]:
                        meilleur = abs(historique_tag[annee])
                resultat[annee] = meilleur
    return resultat


SEUIL_CAPEX_REVENUE = 1.2 # Un capex superieur a 1,2 fois le revenue est ecarte (total avec acquisitions) ; les producteurs de petrole depassent souvent 80 %

def _positif(donnees, nom_tag):
    return {annee: abs(v) for annee, v in extraire_historique_annuel(donnees, nom_tag).items()}

def extraire_capex(donnees, revenue): # Garde le plus grand des tags principaux ; une valeur n'est ecartee que si elle est aberrante (voir garde)
    historiques = {t: _positif(donnees, t) for t in TAGS_CAPEX}
    resultat = {}
    for tag, historique in historiques.items():
        for annee in historique:
            valeur = historique[annee]
            voisins = [historique[annee + d] for d in (-1, 1) if annee + d in historique]
            if len(voisins) > 0 and valeur > 2.5 * max(voisins): # Garde : saut isole par rapport aux annees voisines du meme tag
                continue
            if len(voisins) == 0 and annee in revenue and revenue[annee] > 0 and valeur > SEUIL_CAPEX_REVENUE * revenue[annee]:
                continue # Garde : sans voisin pour comparer, un capex > 1,2 x revenue est ecarte
            if annee not in resultat or valeur > resultat[annee]:
                resultat[annee] = valeur
    petrole = set()
    for tag in TAGS_CAPEX_PETROLE:
        petrole |= set(historiques.get(tag, {}))
    for nom_tag in TAGS_CAPEX_DERNIER_RECOURS: # Tag d'acquisitions de gisements : dernier recours
        for annee, valeur in _positif(donnees, nom_tag).items():
            if annee not in resultat: # aucune autre valeur
                resultat[annee] = valeur
            elif annee not in petrole and resultat[annee] < 0.25 * valeur: # seulement de petits tags (PXD) et aucun tag petrolier propre
                resultat[annee] = valeur
    return resultat

def valeurs_absolues(historique): # Renvoie une copie de l'historique avec toutes les valeurs positives
    resultat = {}
    for annee in historique:
        resultat[annee] = abs(historique[annee])
    return resultat

def corriger_dette_totale(donnees, dette_lt): # LongTermDebt est un total qui inclut la part courante : on la retire pour ne pas la compter deux fois
    total = valeurs_absolues(extraire_historique_annuel(donnees, 'LongTermDebt'))
    non_courante = valeurs_absolues(extraire_historique_annuel(donnees, 'LongTermDebtNoncurrent'))
    avec_leasing = valeurs_absolues(extraire_historique_annuel(donnees, 'LongTermDebtAndCapitalLeaseObligations'))
    part_courante = valeurs_absolues(extraire_historique_annuel(donnees, 'LongTermDebtCurrent'))
    part_courante_leasing = valeurs_absolues(extraire_historique_annuel(donnees, 'LongTermDebtAndCapitalLeaseObligationsCurrent'))
    for annee in part_courante_leasing: # Si LongTermDebtCurrent est absent, on prend la part courante avec leasing
        if annee not in part_courante:
            part_courante[annee] = part_courante_leasing[annee]

    for annee in dette_lt:
        if annee in total and non_courante.get(annee, 0) == 0 and avec_leasing.get(annee, 0) == 0: # La dette long terme vient bien du total (une dette non courante publiee a 0 compte comme absente)
            if dette_lt[annee] == total[annee] and annee in part_courante:
                if part_courante[annee] > 0 and part_courante[annee] <= total[annee]: # Si la part courante egale le total, toute la dette est courante et la part long terme vaut 0
                    dette_lt[annee] = total[annee] - part_courante[annee]
    return dette_lt

TAGS_REFERENCE_ACTIONS = ['WeightedAverageNumberOfSharesOutstandingBasic', 'WeightedAverageNumberOfDilutedSharesOutstanding'] # Nombre moyen d'actions de l'annee, sert de reference d'echelle
SEUIL_ACTIONS_MIN = 1000000 # En dessous, le nombre d'actions est considere comme mal echelonne
SEUIL_ACTIONS_MAX = 100000000000 # Aucune entreprise du S&P 500 n'a autant d'actions
SEUIL_ACTIONS_SUSPECT = 10000000 # Une valeur plus petite peut etre une valeur en milliers

def nettoyer_actions(historique, reference): # Corrige les actions mal echelonnees, supprime les valeurs bidon
    valides_annee = {} # annee -> valeur plausible, sert de point de comparaison
    for annee in historique:
        if historique[annee] is not None and historique[annee] >= SEUIL_ACTIONS_MIN and historique[annee] <= SEUIL_ACTIONS_MAX:
            valides_annee[annee] = historique[annee]

    resultat = {}
    for annee in historique:
        valeur = historique[annee]
        if valeur is None or valeur <= 0 or valeur in [1, 10, 100, 1000, 10000]: # Valeurs bidon (filiales, zeros)
            continue

        corrigee = False
        if annee in reference and reference[annee] > 0: # Regle 1 : comparaison avec le nombre moyen d'actions de la meme annee
            rapport = valeur / reference[annee]
            for facteur in [1000, 1000000]:
                if rapport >= 0.4 * facteur and rapport <= 2.5 * facteur and valeur / facteur >= SEUIL_ACTIONS_MIN: # Trop grande
                    resultat[annee] = valeur / facteur
                    corrigee = True
                    break
                if valeur < SEUIL_ACTIONS_SUSPECT and rapport >= 0.4 / facteur and rapport <= 2.5 / facteur: # Trop petite
                    resultat[annee] = valeur * facteur
                    corrigee = True
                    break
        if corrigee:
            continue

        if valeur > SEUIL_ACTIONS_MAX: # Regle 3 : valeur impossible, on teste en milliers
            essai = valeur
            while essai > SEUIL_ACTIONS_MAX:
                essai = essai / 1000
            if essai >= SEUIL_ACTIONS_MIN:
                resultat[annee] = essai
        elif valeur < SEUIL_ACTIONS_MIN: # Regle 2 : valeur trop petite, on compare a l'annee valide la plus proche
            voisine = None
            ecart = 1000
            for autre in valides_annee:
                if abs(autre - annee) < ecart:
                    ecart = abs(autre - annee)
                    voisine = valides_annee[autre]
            if voisine is not None:
                for facteur in [1000, 1000000]:
                    essai = valeur * facteur
                    if essai >= 0.5 * voisine and essai <= 2 * voisine:
                        resultat[annee] = essai
                        break
        else: # Valeur plausible
            resultat[annee] = valeur
    return resultat

def harmoniser_echelle(historique): # Un saut de x1000 d'une annee a l'autre n'existe pas : on suit l'annee la plus recente
    resultat = {}
    suivante = None
    for annee in sorted(historique, reverse=True):
        valeur = historique[annee]
        if suivante is not None:
            rapport = valeur / suivante
            if rapport >= 600 and rapport <= 1500:
                valeur = valeur / 1000
            elif rapport >= 1 / 1500 and rapport <= 1 / 600:
                valeur = valeur * 1000
        resultat[annee] = valeur
        suivante = valeur
    return resultat

def extraire_actions_couverture(donnees): # Actions de la page de couverture du 10-K (taxonomie dei), classees par annee de cloture comme le reste
    resultat = {}
    dates_depot = {}

    if '_fins_exercice' not in donnees: # Meme calcul que dans extraire_historique_annuel
        donnees['_fins_exercice'] = trouver_fins_exercice(donnees)
    clotures = sorted(donnees['_fins_exercice']) # Dates de cloture, de la plus ancienne a la plus recente

    entrees = donnees.get('facts', {}).get('dei', {}).get('EntityCommonStockSharesOutstanding', {}).get('units', {}).get('shares', [])
    for entree in entrees:
        if entree.get('form', '') == '10-K' and entree.get('fp', '') == 'FY' and entree.get('fy') is not None:
            depot = entree.get('filed', '')

            cloture_retenue = None
            for cloture in clotures: # La derniere cloture situee avant la date de depot
                if cloture.isoformat() < depot:
                    cloture_retenue = cloture

            if cloture_retenue is not None and (date.fromisoformat(depot) - cloture_retenue).days <= 200:
                annee = (cloture_retenue - timedelta(days=15)).year # Meme regle que pour les autres valeurs
            else:
                annee = int(entree.get('fy')) # Cloture inconnue : on garde l'annee fiscale declaree

            if annee not in resultat or depot < dates_depot[annee]:
                resultat[annee] = entree.get('val')
                dates_depot[annee] = depot
    return resultat

def extraire_actions(donnees): # Nettoie chaque tag separement, puis remplit les annees manquantes dans l'ordre de priorite
    reference = extraire_avec_candidats(donnees, TAGS_REFERENCE_ACTIONS, 'shares')
    resultat = {}

    for nom_tag in TAGS_SHARES_OUTSTANDING: # Un tag a 0 ou a une valeur bidon ne masque plus les tags suivants
        propre = nettoyer_actions(extraire_historique_annuel(donnees, nom_tag, 'shares'), reference)
        for annee in propre:
            if annee not in resultat:
                resultat[annee] = propre[annee]

    emises = extraire_historique_annuel(donnees, 'CommonStockSharesIssued', 'shares')
    propres = extraire_historique_annuel(donnees, 'TreasuryStockShares', 'shares')
    emises_moins_propres = {}
    for annee in emises:
        if annee in propres and emises[annee] - propres[annee] > 0:
            emises_moins_propres[annee] = emises[annee] - propres[annee]

    for historique_repli in [emises_moins_propres, extraire_actions_couverture(donnees), emises]: # Replis dans cet ordre
        propre = nettoyer_actions(historique_repli, reference)
        for annee in propre:
            if annee not in resultat:
                resultat[annee] = propre[annee]

    return harmoniser_echelle(resultat)

TAGS_RESULTAT_NET = ['ProfitLoss', 'NetIncomeLoss'] # Sert a reconstituer le resultat avant impot
def extraire_cash_v3(donnees): # v3 : tresorerie + placements a court terme (le total publie s'il existe, sinon tresorerie + premier tag de placements)
    base = extraire_avec_candidats(donnees, TAGS_CASH)
    total = extraire_historique_annuel(donnees, 'CashCashEquivalentsAndShortTermInvestments')
    placements = {}
    for nom_tag in TAGS_ST_INVEST:
        h = extraire_historique_annuel(donnees, nom_tag)
        for annee in h:
            if annee not in placements:
                placements[annee] = abs(h[annee])
    resultat = dict(base)
    for annee in placements:
        if annee in total and annee in base and total[annee] >= base[annee]:
            resultat[annee] = total[annee]
        elif annee in base:
            resultat[annee] = base[annee] + placements[annee]
        elif annee in total:
            resultat[annee] = total[annee]
    for annee in total:
        if annee not in placements and annee in base and total[annee] > base[annee]:
            resultat[annee] = total[annee]
    non_courants = {}
    for nom_tag in TAGS_LT_SECURITIES: # titres non courants : premier tag disponible par annee, ajoute a la tresorerie
        h = extraire_historique_annuel(donnees, nom_tag)
        for annee in h:
            if annee not in non_courants:
                non_courants[annee] = abs(h[annee])
    for annee in non_courants:
        if annee in resultat:
            resultat[annee] += non_courants[annee]
    return resultat

NOMS_METRIQUES = ['revenue', 'ebit', 'da', 'income_tax', 'interest', 'ocf', 'capex', 'cash', 'long_term_debt', 'current_debt', 'shares', 'pretax']

def corriger_doublon_dette(dette_lt, dette_ct): # Si la dette long terme est exactement egale a la dette courante, c'est un total deja compte une fois : toute la dette est courante
    for annee in dette_lt:
        if annee in dette_ct:
            if dette_lt[annee] > 0 and dette_lt[annee] == dette_ct[annee]:
                dette_lt[annee] = 0
    return dette_lt

def extraire_toutes_metriques(donnees): # Renvoie un dictionnaire : nom de la metrique -> {annee: valeur}
    historiques = {}
    historiques['revenue'] = extraire_revenue(donnees)
    historiques['ebit'] = extraire_avec_candidats(donnees, TAGS_EBIT)
    historiques['da'] = extraire_da(donnees)
    historiques['income_tax'] = extraire_avec_candidats(donnees, TAGS_INCOME_TAX)
    historiques['interest'] = extraire_avec_candidats(donnees, TAGS_INTEREST_EXPENSE)
    historiques['ocf'] = extraire_avec_candidats(donnees, TAGS_OCF)
    historiques['capex'] = extraire_capex(donnees, historiques['revenue']) # Le revenue sert de garde-fou contre les totaux aberrants
    for annee in historiques['interest']: # Une charge d'interet est positive (idem)
        historiques['interest'][annee] = abs(historiques['interest'][annee])
    historiques['cash'] = extraire_cash_v3(donnees)
    historiques['long_term_debt'] = extraire_dette(donnees, TAGS_LONG_TERM_DEBT)
    historiques['current_debt'] = extraire_dette(donnees, TAGS_CURRENT_DEBT)
    historiques['long_term_debt'] = corriger_dette_totale(donnees, historiques['long_term_debt']) # Evite de compter la part courante deux fois
    historiques['long_term_debt'] = corriger_doublon_dette(historiques['long_term_debt'], historiques['current_debt']) # Evite de compter deux fois une dette entierement courante
    historiques['shares'] = extraire_actions(donnees)
    historiques['pretax'] = extraire_avec_candidats(donnees, TAGS_PRETAX_INCOME)
    resultat_net = extraire_avec_candidats(donnees, TAGS_RESULTAT_NET)
    for annee in resultat_net: # Resultat avant impot manquant : on le reconstitue par resultat net + impot
        if annee not in historiques['pretax'] and annee in historiques['income_tax']:
            historiques['pretax'][annee] = resultat_net[annee] + historiques['income_tax'][annee]
    return historiques

def dette_manquante_materielle(interets, dette_totale, ocf): # True si la dette que laissent supposer les interets depasse nettement la dette lue
    if interets is None or abs(interets) <= SEUIL_INTERETS_DETTE_NULLE:
        return False
    if abs(interets) <= TAUX_INTERET_MAX * dette_totale: # Taux d'interet plausible : la dette lue est coherente
        return False
    if ocf is None or ocf == 0: # Pas de cash flow pour juger la materialite : on prefere ne pas se fier a la dette
        return True
    manquante = abs(interets) / TAUX_DETTE_IMPLICITE - dette_totale
    return manquante > RATIO_MATERIALITE * abs(ocf)

def construire_lignes_annuelles(historiques): # Une ligne par annee ou revenue ou ocf existe
    annees = set()
    for annee in historiques['revenue']:
        annees.add(annee)
    for annee in historiques['ocf']:
        annees.add(annee)

    lignes = []
    for annee in sorted(annees):
        ligne = {}
        ligne['annee'] = annee
        for nom in NOMS_METRIQUES:
            ligne[nom] = historiques[nom].get(annee) # None si la metrique n'existe pas cette annee

        if ligne['ebit'] is not None: # EBIT publie par l'entreprise
            ligne['ebit_source'] = 'reel'
        elif ligne['pretax'] is not None and ligne['interest'] is not None: # Sinon : resultat avant impot + interets
            ligne['ebit'] = ligne['pretax'] + ligne['interest'] # EBIT = résultat avant impôt + charge d'intérêt de l'année
            ligne['ebit_source'] = 'approx'
        elif ligne['pretax'] is not None: # Pas de charge d'interet publiee : on suppose des interets negligeables
            ligne['ebit'] = ligne['pretax']
            ligne['ebit_source'] = 'approx_sans_interets'
        else:
            ligne['ebit_source'] = 'absent'

        dette_lt = ligne['long_term_debt'] # Dette long terme publiee (None si absente)
        dette_ct = ligne['current_debt'] # Dette court terme publiee (None si absente)
        interets = ligne['interest']

        if dette_lt is None and dette_ct is None: # Aucune dette publiee cette annee
            if dette_manquante_materielle(interets, 0, ligne['ocf']): # Des interets importants face au cash flow : la dette existe mais n'est pas lue
                ligne['dette_statut'] = 'inconnue'
            else: # Pas d'interets : on considere qu'il n'y a pas de dette
                ligne['long_term_debt'] = 0
                ligne['current_debt'] = 0
                ligne['dette_statut'] = 'nulle'
        else: # Au moins une des deux dettes est publiee, l'autre vaut 0
            if dette_lt is None:
                ligne['long_term_debt'] = 0
            if dette_ct is None:
                ligne['current_debt'] = 0
            ligne['dette_statut'] = 'publiee'
            dette_totale = ligne['long_term_debt'] + ligne['current_debt']
            if dette_manquante_materielle(interets, dette_totale, ligne['ocf']): # Dette nulle ou trop petite face aux interets et au cash flow : la vraie dette n'est pas lue
                ligne['long_term_debt'] = None
                ligne['current_debt'] = None
                ligne['dette_statut'] = 'inconnue'

        lignes.append(ligne)
    return lignes

def dates_depot_par_annee(donnees): # {annee: date de depot du 10-K dont vient l'OCF retenu} ; les tags sont pris dans l'ordre de priorite, comme pour l'OCF
    resultat = {}
    for nom_tag in TAGS_OCF:
        for annee, depot in donnees.get('_depots', {}).get(nom_tag, {}).items():
            if annee not in resultat and depot != '':
                resultat[annee] = depot
    return resultat

def dates_cloture_par_annee(donnees): # {annee: 'AAAA-MM-JJ'} : date de cloture reelle de chaque exercice, avec la meme regle d'annee que le reste (fin - 15 jours)
    if '_fins_exercice' not in donnees:
        donnees['_fins_exercice'] = trouver_fins_exercice(donnees)
    resultat = {}
    for fin in donnees['_fins_exercice']:
        annee = (fin - timedelta(days=15)).year
        if annee not in resultat or fin > resultat[annee]: # Si deux clotures tombent la meme annee (changement de date d'exercice), on garde la plus tardive
            resultat[annee] = fin
    return {annee: resultat[annee].isoformat() for annee in resultat}

def charger_dette_manuelle(chemin): # Lit dette_manuelle.csv : dette lue a la main dans un 10-K quand companyfacts ne l'a pas
    table = {}
    if not os.path.exists(chemin):
        return table
    fichier = open(chemin, 'r', encoding='utf-8-sig')
    lecteur = csv.DictReader(fichier)
    for ligne in lecteur:
        cle = (str(int(ligne['cik'])), int(ligne['annee']))
        table[cle] = (int(float(ligne['long_term_debt'])), int(float(ligne['current_debt'])))
    fichier.close()
    return table

def appliquer_dette_manuelle(cik, lignes, dette_manuelle): # Une ligne presente dans dette_manuelle.csv prend toujours la dette lue a la main (meme si companyfacts publiait une dette trop petite)
    for ligne in lignes:
        cle = (str(int(cik)), ligne['annee'])
        if cle in dette_manuelle:
            ligne['long_term_debt'] = dette_manuelle[cle][0]
            ligne['current_debt'] = dette_manuelle[cle][1]
            ligne['dette_statut'] = 'manuelle'
    return lignes

def ligne_exploitable(ligne): # 'oui' si la ligne est complete pour le reverse DCF, sinon 'non'
    if ligne['annee'] < 2010: # Avant 2010, companyfacts n'a pas de bilan exploitable
        return 'non'
    for nom in ['capex', 'ocf', 'shares', 'cash']: # Le reverse DCF utilise OCF, capex, interets, cash, dette, actions (ebit et da ne servent plus). Le cash sert au passage de la valeur d'entreprise aux fonds propres
        if ligne[nom] is None:
            return 'non'
    if ligne['dette_statut'] == 'inconnue':
        return 'non'
    return 'oui'

RATIO_REVENUE_MIN = 0.3 # En dessous, la variation annuelle du revenue est signalee
RATIO_REVENUE_MAX = 3.0 # Au dessus, elle est signalee aussi

def controler_lignes(lignes): # Renvoie la liste des alertes de coherence pour une entreprise
    alertes = []
    precedente = None

    for ligne in lignes:
        annee = ligne['annee']

        if ligne['revenue'] is not None and ligne['revenue'] <= 0:
            alertes.append(str(annee) + ' : revenue negatif ou nul')
        if ligne['capex'] is not None and ligne['capex'] < 0:
            alertes.append(str(annee) + ' : capex negatif (signe a verifier)')
        if ligne['capex'] is not None and ligne['ocf'] is not None and ligne['ocf'] > 0 and ligne['capex'] > 2 * ligne['ocf']:
            alertes.append(str(annee) + ' : capex superieur a 2 fois l ocf (a verifier)')
        if ligne['cash'] is not None and ligne['cash'] < 0:
            alertes.append(str(annee) + ' : cash negatif')

        if precedente is not None:
            if annee - precedente['annee'] > 1: # Il manque au moins une annee entre les deux
                alertes.append(str(precedente['annee']) + ' -> ' + str(annee) + ' : annee(s) manquante(s)')
            elif precedente['revenue'] is not None and ligne['revenue'] is not None and precedente['revenue'] > 0:
                ratio = ligne['revenue'] / precedente['revenue']
                if ratio < RATIO_REVENUE_MIN or ratio > RATIO_REVENUE_MAX:
                    alertes.append(str(annee) + ' : revenue x' + str(round(ratio, 2)) + ' par rapport a ' + str(precedente['annee']))

        precedente = ligne
    return alertes

def ecrire_fondamentaux(liste_ciks, chemin_fondamentaux, chemin_alertes, chemin_dette_manuelle='dette_manuelle.csv'): # Ecrit un tableau annuel par entreprise et un fichier d'alertes
    if not os.path.isdir(DOSSIER_CACHE) or len(os.listdir(DOSSIER_CACHE)) == 0: # Garde-fou : sans cache, le fichier de sortie serait ecrase par un fichier vide
        raise SystemExit('Dossier Companyfacts absent ou vide (' + DOSSIER_CACHE + ') : lancer d\'abord py a02_main.py (variable SEC_USER_AGENT requise)')
    sortie = open(chemin_fondamentaux + '.tmp', 'w', newline='', encoding='utf-8') # ecriture dans .tmp, renommee a la fin : un arret ne laisse pas un fichier partiel
    ecrivain = csv.writer(sortie)
    ecrivain.writerow(['cik', 'annee'] + NOMS_METRIQUES + ['ebit_source', 'dette_statut', 'exploitable', 'date_cloture', 'interest_source', 'date_depot', 'depart_estime'])

    sortie_alertes = open(chemin_alertes + '.tmp', 'w', newline='', encoding='utf-8')
    ecrivain_alertes = csv.writer(sortie_alertes)
    ecrivain_alertes.writerow(['cik', 'nom', 'alerte'])

    dette_manuelle = charger_dette_manuelle(chemin_dette_manuelle)
    nombre_total = len(liste_ciks)
    compteur = 0
    nombre_ecrits = 0
    for cik in liste_ciks:
        compteur = compteur + 1
        prefixe = str(compteur) + '/' + str(nombre_total) + ' : CIK ' + cik
        chemin_fichier = os.path.join(DOSSIER_CACHE, 'CIK' + cik.zfill(10) + '.json')

        if not os.path.exists(chemin_fichier): # CIK en 404 ou jamais telecharge
            print(prefixe + ' pas de donnee')
            ecrivain_alertes.writerow([cik, '', 'fichier absent du cache'])
            continue

        fichier = open(chemin_fichier, 'r', encoding='utf-8')
        donnees = json.loads(fichier.read())
        fichier.close()
        nom = donnees.get('entityName', '')

        lignes = construire_lignes_annuelles(extraire_toutes_metriques(donnees))
        lignes = appliquer_dette_manuelle(cik, lignes, dette_manuelle)
        depots = dates_depot_par_annee(donnees)
        clotures = dates_cloture_par_annee(donnees) # Date de cloture de chaque annee, utilisee pour aller chercher le cours de bourse

        if len(lignes) == 0: # Aucune annee exploitable (societe etrangere, pas de 10-K XBRL...)
            print(prefixe + ' ' + nom + ' : aucune annee exploitable')
            ecrivain_alertes.writerow([cik, nom, 'aucune annee exploitable'])
            continue

        for ligne in lignes:
            source_interet = '' # 'publie' : lu dans le 10-K ; 'estime' : dette x TAUX_DETTE_IMPLICITE faute d'interet publie ; vide : ni interet ni dette
            if ligne['interest'] is not None:
                source_interet = 'publie'
            else:
                dette_totale = (ligne['long_term_debt'] or 0) + (ligne['current_debt'] or 0)
                if dette_totale > 0:
                    ligne['interest'] = dette_totale * TAUX_DETTE_IMPLICITE
                    source_interet = 'estime'
            valeurs = [cik, ligne['annee']]
            for nom_metrique in NOMS_METRIQUES:
                valeurs.append(ligne[nom_metrique])
            valeurs.append(ligne['ebit_source'])
            valeurs.append(ligne['dette_statut'])
            valeurs.append(ligne_exploitable(ligne))
            valeurs.append(clotures.get(ligne['annee'], ''))
            valeurs.append(source_interet)
            depot = depots.get(ligne['annee'], '')
            estime = 'non'
            cloture_texte = clotures.get(ligne['annee'], '')
            if depot != '' and cloture_texte != '' and not (0 <= (date.fromisoformat(depot) - date.fromisoformat(cloture_texte)).days <= 200):
                depot = '' # Depot avant la cloture ou plus de 200 jours apres : la valeur retenue ne vient pas du 10-K de cet exercice
            if depot == '' and clotures.get(ligne['annee'], '') != '': # Date de depot absente ou incoherente : cloture + 90 jours, marque
                depot = (date.fromisoformat(clotures[ligne['annee']]) + timedelta(days=90)).isoformat()
                estime = 'oui'
            valeurs.append(depot)
            valeurs.append(estime)
            ecrivain.writerow(valeurs)
        nombre_ecrits = nombre_ecrits + 1
        print(prefixe + ' ' + nom + ' : extrait (' + str(len(lignes)) + ' annees)')

        for alerte in controler_lignes(lignes):
            ecrivain_alertes.writerow([cik, nom, alerte])

    sortie.close()
    sortie_alertes.close()
    os.replace(chemin_fondamentaux + '.tmp', chemin_fondamentaux)
    os.replace(chemin_alertes + '.tmp', chemin_alertes)
    return nombre_ecrits

