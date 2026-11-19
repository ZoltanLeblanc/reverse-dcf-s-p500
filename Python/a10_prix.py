"""Prix de bourse a chaque cloture d'exercice, remis dans l'unite de l'epoque (celle de la colonne shares).
Yahoo donne un cours ajuste des splits : pour retrouver le cours reellement cote ce jour-la, on le multiplie
par le ratio de tous les splits qui ont eu lieu APRES cette date.
Exemple : Apple, cloture 2019-09-28, Yahoo = 55 $ ; split 4 pour 1 en 2020 -> 55 x 4 = 220 $ (cours reel de l'epoque).
Necessite yfinance (pip install yfinance) ; Tiingo sert de seconde source pour les lignes sans prix Yahoo.
Entrees : fondamentaux_sp500.csv, cik_categorie.csv, ticker_cik_sp500.csv, ticker_manuel.csv, caches du dossier Prix.
Sorties : prix_cloture.csv, alertes_prix.csv, caches par ticker et listes d'introuvables dans le dossier Prix.
Fonctions principales :
- obtenir_historique / obtenir_historique_tiingo : historique d'un ticker, cache d'abord puis Yahoo ou Tiingo.
- prix_a_la_date / rendement_total : cours de cloture remis a l'echelle de l'epoque, rendements a 1 et 3 ans.
- corriger_unite_des_actions : aligne l'unite des actions du 10-K sur celle du cours (split avant le depot).
- lancer_controles : alertes sur ticker reutilise, valeur isolee, saut de capitalisation.
- completer_avec_tiingo : complete les lignes sans prix Yahoo.
- ecrire_prix : enchaine l'ensemble et ecrit les fichiers de sortie."""
import csv
import os
import time
import logging
from bisect import bisect_right
from datetime import date, timedelta
import math
from a01_ticker_CIK import charger_table_ticker_cik


DOSSIER_PRIX = os.environ.get("DOSSIER_PRIX", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Prix")) # Un petit fichier par ticker : on ne retelecharge jamais deux fois
CATEGORIES_CIBLES = ['Standard', 'Cyclique']
ANNEE_MIN = 2010
DEBUT_HISTORIQUE = '2008-12-01' # Un peu avant la premiere cloture (2010) pour trouver un cours meme si la cloture tombe un week-end
ECART_MAX_JOURS = 7 # Si le dernier cours connu avant la cloture a plus de 7 jours, on considere qu'il n'y a pas de cours
DELAI_ENTRE_REQUETES = 0.3
TOLERANCE_HORIZON_JOURS = 7 # Cours a 1 an et 3 ans apres le depart : premier jour de bourse a partir de la date cible, a 7 jours au plus (sinon vide)
DELAI_DEPOT_ESTIME = 90 # Sans date de depot du 10-K, le depart est estime a la cloture + 90 jours
RATIOS_CLASSIQUES = [1.25, 4/3, 1.5, 5/3, 2, 2.5, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 25, 30, 40, 50, 100] # Vrais splits ; leur inverse (reverse split) est accepte aussi. Les spin-offs, que Yahoo note comme des splits a ratio irregulier (1,398 ; 2,084...), ne sont pas dans la liste
TOLERANCE_RATIO = 0.001 # Un vrai split a un ratio exact : on accepte 0,1 % d'ecart
JOURS_FENETRE_DERNIERE_ANNEE = 180 # Pour la derniere annee d'une societe, on regarde les splits survenus dans les 180 jours apres la cloture
SEUIL_CAP_REVENU_BAS = 0.03 # Une capitalisation inferieure a 3 % du revenu annuel est impossible en pratique : ticker reutilise par une autre societe ou cours faux
SEUIL_CAP_REVENU_HAUT = 60 # Au dessus, valorisation extreme (croissance : Moderna 2019, Palantir...) : signalee mais gardee
SEUIL_SAUT_CAPITALISATION = 4 # Capitalisation multipliee par 4 ou divisee par 4 d'une annee a l'autre : signalee dans alertes_prix.csv
TIINGO_REQUETES_PAR_HEURE = 300 # Plafond horaire de requetes Tiingo : a verifier sur tiingo.com pour ton forfait et a ajuster ici
STATUTS_A_COMPLETER = ['ticker_introuvable', 'avant_debut_historique', 'pas_de_cours_proche'] # Les lignes sans prix Yahoo : Tiingo essaie de les completer
TIINGO_MAX_NOUVEAUX_PAR_LANCEMENT = None # None = tout télécharger d'un coup (pauses automatiques) ; mettre 45 pour revenir aux lots
HORODATAGES_TIINGO = [] # Heures des dernieres requetes Tiingo, pour respecter le quota horaire
logging.getLogger('yfinance').setLevel(logging.CRITICAL) # Coupe les messages 'possibly delisted' de yfinance (on les compte nous-memes)

def chemin_cache_prix(ticker): # Chemin du fichier cache d'un ticker
    return os.path.join(DOSSIER_PRIX, ticker.replace('.', '-') + '.csv')

def telecharger_historique(ticker): # Renvoie (dates, cours, splits) depuis Yahoo, 'absent' si Yahoo n'a rien pour ce ticker, None si erreur de connexion
    import yfinance as yf # Importe ici pour que le reste du fichier marche meme sans yfinance
    symbole = ticker.replace('.', '-') # Yahoo ecrit BRK-B et non BRK.B
    tableau = None
    for essai in range(2): # Un deuxieme essai uniquement si Yahoo a plante (pas si le ticker n'existe pas)
        try:
            tableau = yf.Ticker(symbole).history(start=DEBUT_HISTORIQUE, auto_adjust=False, actions=True) # auto_adjust=False : Close est ajuste des splits mais pas des dividendes
        except Exception:
            tableau = None
            time.sleep(1)
            continue
        break
    time.sleep(DELAI_ENTRE_REQUETES)
    if tableau is None:
        return None
    if len(tableau) == 0: # Yahoo repond parfois vide quand il est surcharge : on redemande une fois avant de conclure que le ticker n'existe pas
        time.sleep(2)
        try:
            tableau = yf.Ticker(symbole).history(start=DEBUT_HISTORIQUE, auto_adjust=False, actions=True)
        except Exception:
            return None
        if len(tableau) == 0:
            return 'absent'

    dates = []
    cours = []
    splits = []
    ajustes = [] # Adj Close : cours ajuste des splits ET des dividendes (rendement total)
    index = tableau.index
    a_adj = 'Adj Close' in tableau.columns
    for position in range(len(tableau)):
        jour = index[position].date() # La date seule, sans l'heure ni le fuseau
        dates.append(jour)
        cours.append(float(tableau['Close'].iloc[position]))
        ajustes.append(float(tableau['Adj Close'].iloc[position]) if a_adj else None)
        ratio = float(tableau['Stock Splits'].iloc[position])
        if ratio > 0: # 0 = pas de split ce jour-la
            splits.append((jour, ratio))
    if not a_adj or any(a is None or a != a for a in ajustes): # Colonne absente ou incomplete : pas de rendement total pour ce ticker
        ajustes = None
    return dates, cours, splits, ajustes

def ecrire_cache(ticker, historique): # Sauvegarde l'historique telecharge
    dates, cours, splits, ajustes = historique
    splits_par_date = {}
    for jour, ratio in splits:
        splits_par_date[jour] = ratio
    fichier = open(chemin_cache_prix(ticker), 'w', newline='', encoding='utf-8')
    ecrivain = csv.writer(fichier)
    ecrivain.writerow(['date', 'close', 'split', 'adj_close'])
    for position in range(len(dates)):
        ecrivain.writerow([dates[position].isoformat(), cours[position], splits_par_date.get(dates[position], 0), '' if ajustes is None else ajustes[position]])
    fichier.close()

def lire_cache(ticker): # Relit l'historique sauvegarde, ou None s'il n'existe pas
    chemin = chemin_cache_prix(ticker)
    if not os.path.exists(chemin):
        return None
    dates = []
    cours = []
    splits = []
    ajustes = []
    fichier = open(chemin, 'r', encoding='utf-8')
    lecteur = csv.DictReader(fichier)
    for ligne in lecteur:
        jour = date.fromisoformat(ligne['date'])
        dates.append(jour)
        cours.append(float(ligne['close']))
        ajustes.append(float(ligne['adj_close']) if ligne.get('adj_close') not in (None, '') else None)
        if float(ligne['split']) > 0:
            splits.append((jour, float(ligne['split'])))
    fichier.close()
    if any(a is None for a in ajustes): # Ancien cache sans Adj Close : sera retelecharge (l'ancien fichier reste utilise si le telechargement echoue)
        ajustes = None
    return dates, cours, splits, ajustes

def chemin_introuvables(): # Liste des tickers pour lesquels Yahoo n'a rien : on ne les redemande pas a chaque lancement
    return os.path.join(DOSSIER_PRIX, 'introuvables.txt')

def lire_introuvables():
    if not os.path.exists(chemin_introuvables()):
        return set()
    fichier = open(chemin_introuvables(), 'r', encoding='utf-8')
    tickers = set(fichier.read().split())
    fichier.close()
    return tickers

def memoriser_introuvable(ticker):
    if not os.path.exists(DOSSIER_PRIX):
        os.makedirs(DOSSIER_PRIX)
    fichier = open(chemin_introuvables(), 'a', encoding='utf-8')
    fichier.write(ticker + '\n')
    fichier.close()

def obtenir_historique(ticker, introuvables): # Cache d'abord, Yahoo sinon ; None si Yahoo n'a rien
    historique = lire_cache(ticker)
    if historique is not None and historique[3] is not None:
        return historique
    if ticker in introuvables: # Supprimer introuvables.txt pour tout redemander a Yahoo
        return None
    ancien = historique # Cache sans cours ajuste : on le garde tant que le nouveau telechargement n'a pas reussi
    historique = telecharger_historique(ticker)
    if historique == 'absent':
        if ancien is not None:
            return ancien
        introuvables.add(ticker)
        memoriser_introuvable(ticker)
        return None
    if historique is None and ancien is not None:
        return ancien
    if historique is not None:
        if not os.path.exists(DOSSIER_PRIX):
            os.makedirs(DOSSIER_PRIX)
        ecrire_cache(ticker, historique)
    return historique

def lire_token_tiingo(): # La cle Tiingo n'est jamais ecrite dans le code : variable d'environnement TIINGO_TOKEN, ou fichier tiingo_token.txt (une seule ligne)
    token = os.environ.get('TIINGO_TOKEN', '').strip()
    if token == '' and os.path.exists('tiingo_token.txt'):
        fichier = open('tiingo_token.txt', 'r', encoding='utf-8')
        token = fichier.read().strip()
        fichier.close()
    if token == '':
        return None
    return token

def chemin_cache_tiingo(ticker): # Cache des donnees brutes Tiingo : un fichier par ticker
    return os.path.join(DOSSIER_PRIX, 'TIINGO_' + ticker.replace('.', '-') + '.csv')

def chemin_introuvables_tiingo():
    return os.path.join(DOSSIER_PRIX, 'tiingo_introuvables.txt')

def attendre_quota_tiingo(): # Pause si on a deja fait TIINGO_REQUETES_PAR_HEURE requetes dans la derniere heure
    while True:
        maintenant = time.time()
        while len(HORODATAGES_TIINGO) > 0 and maintenant - HORODATAGES_TIINGO[0] > 3600:
            HORODATAGES_TIINGO.pop(0)
        if len(HORODATAGES_TIINGO) < TIINGO_REQUETES_PAR_HEURE:
            break
        attente = 3600 - (maintenant - HORODATAGES_TIINGO[0]) + 5
        print('Tiingo : quota horaire atteint, pause de ' + str(int(attente / 60) + 1) + ' min (le script reprend tout seul)')
        time.sleep(attente)
    HORODATAGES_TIINGO.append(time.time())

def telecharger_tiingo(ticker, token): # Renvoie [(date, close_brut, split)] , 'absent' si Tiingo ne connait pas le ticker, 'cle_invalide', ou None si erreur
    import requests
    symbole = ticker.replace('.', '-') # Tiingo ecrit BRK-B comme Yahoo
    url = 'https://api.tiingo.com/tiingo/daily/' + symbole + '/prices'
    entetes = {'Authorization': 'Token ' + token}
    parametres = {'startDate': DEBUT_HISTORIQUE, 'format': 'csv'}
    for essai in range(3):
        attendre_quota_tiingo()
        try:
            reponse = requests.get(url, headers=entetes, params=parametres, timeout=60)
        except Exception:
            time.sleep(5)
            continue
        if reponse.status_code == 429: # Quota depasse : on attend 15 minutes
            print('Tiingo : limite atteinte (429), pause de 15 min')
            time.sleep(900)
            continue
        if reponse.status_code == 401 or reponse.status_code == 403:
            return 'cle_invalide'
        if reponse.status_code == 404:
            return 'absent'
        if reponse.status_code != 200:
            return None
        texte = reponse.text
        if not texte.startswith('date'): # Pas un tableau csv (message d'erreur, limite de debit renvoyee en 200) : a redemander, pas de liste noire
            return None
        lignes = []
        for ligne in csv.DictReader(texte.splitlines()):
            split = 1.0
            if ligne.get('splitFactor', '') != '':
                split = float(ligne['splitFactor'])
            adj = float(ligne['adjClose']) if ligne.get('adjClose', '') != '' else None # cours ajuste des splits et dividendes
            lignes.append((date.fromisoformat(ligne['date'][:10]), float(ligne['close']), split, adj))
        if len(lignes) == 0:
            return 'absent'
        return lignes
    return None

def convertir_tiingo(lignes): # Transforme les cours bruts Tiingo dans le meme format que Yahoo : (dates, cours ajustes des splits, splits). Le prix d'epoque retrouve alors exactement le cours brut
    lignes = sorted(lignes, key=lambda x: x[0])
    dates = []
    bruts = []
    splits = []
    ajustes = [x[3] for x in lignes]
    if any(a is None for a in ajustes):
        ajustes = None
    for position in range(len(lignes)):
        jour, brut, ratio = lignes[position][:3]
        if abs(ratio - 1) > 0.0001 and position > 0 and brut > 0 and lignes[position - 1][1] > 0: # Verifie le sens du ratio avec le saut de cours : un 2 pour 1 divise le cours par 2
            saut = lignes[position - 1][1] / brut
            if abs(math.log(saut) - math.log(ratio)) > abs(math.log(saut) + math.log(ratio)):
                ratio = 1 / ratio
        dates.append(jour)
        bruts.append(brut)
        splits.append(ratio)
    cours = [0.0] * len(dates)
    cumul = 1.0 # Produit des splits posterieurs a chaque date
    for position in range(len(dates) - 1, -1, -1):
        cours[position] = bruts[position] / cumul
        if abs(splits[position] - 1) > 0.0001:
            cumul = cumul * splits[position]
    liste_splits = []
    for position in range(len(dates)):
        if abs(splits[position] - 1) > 0.0001:
            liste_splits.append((dates[position], splits[position]))
    return dates, cours, liste_splits, ajustes

def ecrire_cache_tiingo(ticker, lignes):
    fichier = open(chemin_cache_tiingo(ticker), 'w', newline='', encoding='utf-8')
    ecrivain = csv.writer(fichier)
    ecrivain.writerow(['date', 'close', 'split', 'adj_close'])
    for jour, brut, ratio, adj in lignes:
        ecrivain.writerow([jour.isoformat(), brut, ratio, '' if adj is None else adj])
    fichier.close()

def lire_cache_tiingo(ticker):
    chemin = chemin_cache_tiingo(ticker)
    if not os.path.exists(chemin):
        return None
    lignes = []
    fichier = open(chemin, 'r', encoding='utf-8')
    for ligne in csv.DictReader(fichier):
        lignes.append((date.fromisoformat(ligne['date']), float(ligne['close']), float(ligne['split']), float(ligne['adj_close']) if ligne.get('adj_close') not in (None, '') else None))
    fichier.close()
    return lignes

def obtenir_historique_tiingo(ticker, token, introuvables): # Cache, puis Tiingo ; renvoie l'historique converti, None, ou 'cle_invalide'
    lignes = lire_cache_tiingo(ticker)
    if lignes is None or any(x[3] is None for x in lignes): # Pas de cache, ou cache sans cours ajuste (ancien format) : on telecharge ; l'ancien cache reste utilise si le telechargement echoue
        ancien = lignes
        if ticker in introuvables and ancien is None:
            return None
        resultat = telecharger_tiingo(ticker, token)
        if ancien is not None and (resultat is None or resultat == 'absent'):
            return convertir_tiingo(ancien)
        if resultat == 'cle_invalide':
            return 'cle_invalide'
        if resultat == 'absent':
            introuvables.add(ticker)
            if not os.path.exists(DOSSIER_PRIX):
                os.makedirs(DOSSIER_PRIX)
            fichier = open(chemin_introuvables_tiingo(), 'a', encoding='utf-8')
            fichier.write(ticker + '\n')
            fichier.close()
            return None
        if resultat is None:
            return None
        lignes = resultat
        if not os.path.exists(DOSSIER_PRIX):
            os.makedirs(DOSSIER_PRIX)
        ecrire_cache_tiingo(ticker, lignes)
    return convertir_tiingo(lignes)

def prix_a_la_date(historique, jour_cloture): # Renvoie (statut, date_du_cours, cours_yahoo, facteur_splits, prix_epoque)
    dates, cours, splits = historique[:3]
    position = bisect_right(dates, jour_cloture) - 1 # Dernier jour de bourse inferieur ou egal a la cloture
    if position < 0:
        return 'avant_debut_historique', '', '', '', ''
    jour_cours = dates[position]
    if (jour_cloture - jour_cours).days > ECART_MAX_JOURS:
        return 'pas_de_cours_proche', jour_cours.isoformat(), '', '', ''
    facteur = 1.0
    for jour_split, ratio in splits:
        if jour_split > jour_cours: # Split posterieur a ce cours : le cours Yahoo est deja divise, on le remet a l'echelle de l'epoque
            facteur = facteur * ratio
    return 'ok', jour_cours.isoformat(), cours[position], facteur, cours[position] * facteur

def rendement_total(historique, ligne): # Cours ajuste (splits + dividendes) a la date du cours de cloture, au depart (1er jour de bourse apres le depot du 10-K), et 1 et 3 ans plus tard. Tout vient de la meme serie
    dates, adj = historique[0], historique[3]
    sortie = {'cours_ajuste': '', 'date_depart': '', 'ajuste_depart': '', 'date_h1': '', 'ajuste_h1': '', 'date_h3': '', 'ajuste_h3': ''}
    if adj is None or ligne['date_cours'] == '':
        return sortie
    sortie['cours_ajuste'] = adj[bisect_right(dates, date.fromisoformat(ligne['date_cours'])) - 1]
    if ligne['date_depot'] == '':
        return sortie
    p = bisect_right(dates, date.fromisoformat(ligne['date_depot'])) # premier jour de bourse strictement apres le depot
    if p >= len(dates):
        return sortie
    depart = dates[p]
    sortie['date_depart'] = depart.isoformat()
    sortie['ajuste_depart'] = adj[p]
    for jours, suffixe in ((365, 'h1'), (1095, 'h3')):
        cible = depart + timedelta(days=jours)
        q = bisect_right(dates, cible - timedelta(days=1)) # premier jour de bourse a partir de la cible
        if q < len(dates) and (dates[q] - cible).days <= TOLERANCE_HORIZON_JOURS:
            sortie['date_' + suffixe] = dates[q].isoformat()
            sortie['ajuste_' + suffixe] = adj[q]
    return sortie

def lire_lignes_cibles(chemin_fondamentaux, chemin_categories): # Lignes exploitables des categories cibles, avec leur ticker
    categories = {}
    fichier = open(chemin_categories, 'r', encoding='utf-8-sig')
    for ligne in csv.DictReader(fichier):
        categories[str(int(ligne['cik']))] = (ligne['ticker'].strip(), ligne['categorie'].strip())
    fichier.close()

    lignes = []
    fichier = open(chemin_fondamentaux, 'r', encoding='utf-8-sig')
    for ligne in csv.DictReader(fichier):
        cik = str(int(ligne['cik']))
        if cik not in categories:
            continue
        ticker, categorie = categories[cik]
        if categorie not in CATEGORIES_CIBLES or ligne['exploitable'] != 'oui' or int(ligne['annee']) < ANNEE_MIN:
            continue
        if ligne['date_cloture'] == '': # Ne devrait pas arriver : relancer a06_lancer_fondamentaux.py
            continue
        lignes.append({'cik': cik, 'annee': int(ligne['annee']), 'ticker': ticker, 'categorie': categorie,
                       'date_cloture': date.fromisoformat(ligne['date_cloture']), 'shares': ligne['shares'], 'revenue': ligne['revenue'],
                       'date_depot': (ligne.get('date_depot') or (date.fromisoformat(ligne['date_cloture']) + timedelta(days=DELAI_DEPOT_ESTIME)).isoformat())})
    fichier.close()
    return lignes

def charger_tickers_manuels(chemin): # Lit ticker_manuel.csv : cik,ticker,raison (ticker Yahoo actuel d'une societe dont la table ticker_cik_sp500.csv garde l'ancien ticker)
    table = {}
    if not os.path.exists(chemin):
        return table
    fichier = open(chemin, 'r', encoding='utf-8-sig')
    for ligne in csv.DictReader(fichier):
        cik = str(int(ligne['cik']))
        if cik not in table:
            table[cik] = []
        table[cik].append(ligne['ticker'].strip())
    fichier.close()
    return table

def tickers_par_cik(table): # {cik: [tickers]} : tous les tickers que la table associe a ce CIK (actuel ou ancien CIK)
    resultat = {}
    for ticker in sorted(table):
        ciks = [str(int(table[ticker]['cik']))]
        for date_bascule, cik_alt in table[ticker]['alternatifs']:
            ciks.append(str(int(cik_alt)))
        for cik in ciks:
            if cik not in resultat:
                resultat[cik] = []
            if ticker not in resultat[cik]:
                resultat[cik].append(ticker)
    return resultat

def ciks_anciens(table): # Ensemble des CIK qui ne sont pas le CIK actuel de leur ticker (ancien CIK apres une reorganisation)
    anciens = set()
    for ticker in table:
        for date_bascule, cik_alt in table[ticker]['alternatifs']:
            anciens.add(str(int(cik_alt)))
    return anciens

def liste_candidats(ticker_principal, tickers_connus, tickers_manuels): # Tickers a essayer pour un CIK, dans l'ordre
    candidats = list(tickers_manuels) + [ticker_principal] + [t for t in tickers_connus if t != ticker_principal]
    resultat = []
    for ticker in candidats:
        if ticker != '' and ticker not in resultat:
            resultat.append(ticker)
    return resultat

def chercher_historique_du_cik(ticker_principal, tickers_connus, introuvables, tickers_manuels=[]): # Essaie les tickers manuels, puis le ticker principal, puis les autres tickers du meme CIK ; renvoie (ticker_utilise, historique, essayes)
    candidats = liste_candidats(ticker_principal, tickers_connus, tickers_manuels)
    essayes = []
    for ticker in candidats:
        if ticker == '' or ticker in essayes:
            continue
        essayes.append(ticker)
        historique = obtenir_historique(ticker, introuvables)
        if historique is not None:
            return ticker, historique, essayes
    return '', None, essayes

def est_split_classique(ratio): # Vrai si le ratio est celui d'un vrai split (2 pour 1, 3 pour 2...) ou de son inverse
    for classique in RATIOS_CLASSIQUES:
        if abs(ratio / classique - 1) < TOLERANCE_RATIO or abs(ratio * classique - 1) < TOLERANCE_RATIO:
            return True
    return False

def splits_classiques_entre(splits, debut_exclu, fin_incluse): # [(date, ratio)] des vrais splits survenus apres debut_exclu et jusqu'a fin_incluse
    resultat = []
    for jour, ratio in splits:
        if jour > debut_exclu and jour <= fin_incluse and est_split_classique(ratio):
            resultat.append((jour, ratio))
    return resultat

def ajouter_note(resultat, note): # Accumule les remarques d'une ligne dans la colonne verifier
    if resultat['verifier'] != '':
        resultat['verifier'] = resultat['verifier'] + ' ; '
    resultat['verifier'] = resultat['verifier'] + note

def corriger_unite_des_actions(resultats_cik): # Un split survenu apres la cloture mais avant le depot du 10-K : les actions du 10-K sont deja apres le split alors que le cours de cloture est avant
    u_suivant = 1.0 # Echelle des actions de l'annee suivante, deja decidee (on remonte de la plus recente a la plus ancienne)
    for annee in sorted(resultats_cik, reverse=True):
        ligne = resultats_cik[annee]
        suivante = resultats_cik.get(annee + 1)
        if suivante is not None:
            fin_fenetre = suivante['date_cloture']
        else:
            fin_fenetre = ligne['date_cloture'] + timedelta(days=JOURS_FENETRE_DERNIERE_ANNEE)

        fenetre = splits_classiques_entre(ligne['splits'], ligne['date_cloture'], fin_fenetre) # Splits de la source qui a fourni le cours de cette ligne
        s = 1.0
        for jour, ratio in fenetre:
            s = s * ratio
        u = 1.0
        if abs(s - 1) > 0.001 and ligne['shares'] != '': # Il y a eu un vrai split apres la cloture : on regarde dans quelle echelle sont les actions
            if suivante is None or suivante['shares'] == '':
                ajouter_note(ligne, 'split apres la cloture, echelle des actions non verifiable (derniere annee)')
            else:
                x = (float(suivante['shares']) / u_suivant) / float(ligne['shares']) # Rapport des actions de l'annee suivante (ramenees a leur cloture) a celles de cette annee
                distance_avant = abs(math.log(x / s)) # Si les actions de cette annee sont avant le split, x doit valoir s
                distance_apres = abs(math.log(x)) # Si elles sont deja apres le split, x doit valoir 1
                if distance_apres <= 0.5 * distance_avant and distance_apres < 0.4:
                    u = s
                    if ligne['statut'] == 'ok':
                        ligne['facteur'] = ligne['facteur'] / s
                        ligne['prix'] = ligne['cours_yahoo'] * ligne['facteur']
                        ligne['ajustement'] = s
                        ajouter_note(ligne, 'actions deja apres le split ' + fenetre[0][0].isoformat() + ' (cours ramene a la meme echelle)')
                elif not (distance_avant <= 0.5 * distance_apres and distance_avant < 0.4):
                    ajouter_note(ligne, 'split apres la cloture, echelle des actions incertaine')
        u_suivant = u

def lancer_controles(resultats_cik): # Controles de coherence apres correction : ticker reutilise, action isolee fausse, saut de capitalisation. Renvoie les alertes
    alertes = []
    annees = sorted(resultats_cik)
    for annee in annees:
        ligne = resultats_cik[annee]
        if ligne['statut'] != 'ok':
            continue
        if ligne['revenue'] != '' and float(ligne['revenue']) > 0:
            rapport = ligne['capitalisation'] / float(ligne['revenue'])
            if rapport < SEUIL_CAP_REVENU_BAS:
                ligne['statut'] = 'douteux'
                ajouter_note(ligne, 'capitalisation = ' + str(round(rapport, 4)) + ' x le revenu : ticker reutilise par une autre societe ou cours faux')
            elif rapport > SEUIL_CAP_REVENU_HAUT:
                ajouter_note(ligne, 'valorisation extreme : ' + str(round(rapport)) + ' x le revenu')

        precedente = resultats_cik.get(annee - 1)
        suivante = resultats_cik.get(annee + 1)
        if precedente is not None and suivante is not None and ligne['shares'] != '' and precedente['shares'] != '' and suivante['shares'] != '':
            q1 = float(ligne['shares']) / float(precedente['shares'])
            q2 = float(ligne['shares']) / float(suivante['shares'])
            if (q1 > 5 and q2 > 5) or (q1 < 0.2 and q2 < 0.2): # Une seule annee tres differente des deux voisines : valeur mal lue
                ligne['statut'] = 'douteux'
                ajouter_note(ligne, 'nombre d actions isole et incoherent avec les annees voisines : verifier le 10-K')

    for annee in annees: # Sauts de capitalisation d'une annee a l'autre
        if annee + 1 in resultats_cik:
            a = resultats_cik[annee]
            b = resultats_cik[annee + 1]
            if a['statut'] == 'ok' and b['statut'] == 'ok' and a['capitalisation'] > 0:
                q = b['capitalisation'] / a['capitalisation']
                if q > SEUIL_SAUT_CAPITALISATION or q < 1 / SEUIL_SAUT_CAPITALISATION:
                    alertes.append('saut de capitalisation x' + str(round(q, 2)) + ' entre ' + str(annee) + ' et ' + str(annee + 1))
    return alertes

def completer_avec_tiingo(ciks, resultats, ticker_principal, connus, manuels, ecrivain_alertes): # Pour chaque ligne sans prix Yahoo, cherche le cours brut chez Tiingo (qui garde les societes disparues)
    token = lire_token_tiingo()
    if token is None:
        print('Tiingo : pas de cle (variable TIINGO_TOKEN ou fichier tiingo_token.txt) : etape ignoree')
        return
    introuvables = set()
    if os.path.exists(chemin_introuvables_tiingo()):
        fichier = open(chemin_introuvables_tiingo(), 'r', encoding='utf-8')
        introuvables = set(fichier.read().split())
        fichier.close()

    a_traiter = []
    for cik in ciks:
        for annee in resultats[cik]:
            if resultats[cik][annee]['statut'] in STATUTS_A_COMPLETER:
                a_traiter.append(cik)
                break
    def nombre_manquantes(cik):
        return len([annee for annee in resultats[cik] if resultats[cik][annee]['statut'] in STATUTS_A_COMPLETER])
    a_traiter = sorted(a_traiter, key=nombre_manquantes, reverse=True) # Les societes qui ont le plus de lignes sans prix d'abord : on peut interrompre le script sans perdre l'essentiel
    print('Tiingo : ' + str(len(a_traiter)) + ' CIK avec des lignes sans prix (les plus touches d\'abord)')

    compteur = 0
    nouveaux = 0 # Tickers telecharges pendant ce lancement
    arret = False
    for cik in a_traiter:
        if arret:
            break
        compteur = compteur + 1
        manquantes = [annee for annee in resultats[cik] if resultats[cik][annee]['statut'] in STATUTS_A_COMPLETER]
        total = len(manquantes)
        for ticker in liste_candidats(ticker_principal[cik], connus.get(cik, []), manuels.get(cik, [])):
            if len(manquantes) == 0:
                break
            deja_connu = os.path.exists(chemin_cache_tiingo(ticker)) or ticker in introuvables # En cache : aucune requete
            if not deja_connu:
                if TIINGO_MAX_NOUVEAUX_PAR_LANCEMENT is not None and nouveaux >= TIINGO_MAX_NOUVEAUX_PAR_LANCEMENT:
                    arret = True
                    break
                nouveaux = nouveaux + 1
            historique = obtenir_historique_tiingo(ticker, token, introuvables)
            if historique == 'cle_invalide':
                print('Tiingo : cle refusee (401/403), etape abandonnee. Verifie la cle dans tiingo_token.txt')
                ecrivain_alertes.writerow(['', '', 'Tiingo : cle refusee'])
                return
            if historique is None:
                continue
            for annee in list(manquantes):
                ligne = resultats[cik][annee]
                statut, date_cours, cours_ajuste, facteur, prix = prix_a_la_date(historique, ligne['date_cloture'])
                if statut == 'ok':
                    ligne['statut'] = 'ok'
                    ligne['ticker_final'] = ticker
                    ligne['date_cours'] = date_cours
                    ligne['cours_yahoo'] = cours_ajuste
                    ligne['facteur'] = facteur
                    ligne['prix'] = prix
                    ligne['splits'] = historique[2]
                    ligne['hist'] = historique
                    ligne['source_prix'] = 'tiingo'
                    ajouter_note(ligne, 'cours Tiingo (ticker ' + ticker + ')')
                    manquantes.remove(annee)
        if not arret:
            print('Tiingo ' + str(compteur) + '/' + str(len(a_traiter)) + ' CIK ' + cik + ' : ' + str(total - len(manquantes)) + ' lignes completees sur ' + str(total))
    if arret:
        print('Tiingo : ' + str(nouveaux) + ' nouveaux tickers telecharges ce lancement. Relance a10_prix.py dans une heure pour continuer (le cache garde tout).')

def ecrire_prix(chemin_fondamentaux, chemin_categories, chemin_table, chemin_sortie, chemin_alertes, chemin_manuels='ticker_manuel.csv'):
    lignes = lire_lignes_cibles(chemin_fondamentaux, chemin_categories)
    table = charger_table_ticker_cik(chemin_table)
    anciens = ciks_anciens(table)
    connus = tickers_par_cik(table)
    manuels = charger_tickers_manuels(chemin_manuels)
    introuvables = lire_introuvables()

    ticker_principal = {} # cik -> ticker de cik_categorie.csv
    for ligne in lignes:
        ticker_principal[ligne['cik']] = ligne['ticker']
    ciks = sorted(ticker_principal, key=int)
    print(str(len(lignes)) + ' lignes, ' + str(len(ciks)) + ' CIK')

    historiques = {} # cik -> (ticker_utilise, historique) ou None
    sortie_alertes = open(chemin_alertes, 'w', newline='', encoding='utf-8')
    ecrivain_alertes = csv.writer(sortie_alertes)
    ecrivain_alertes.writerow(['cik', 'ticker', 'alerte'])
    compteur = 0
    for cik in ciks:
        compteur = compteur + 1
        ticker_utilise, historique, essayes = chercher_historique_du_cik(ticker_principal[cik], connus.get(cik, []), introuvables, manuels.get(cik, []))
        if historique is None:
            historiques[cik] = None
            print(str(compteur) + '/' + str(len(ciks)) + ' CIK ' + cik + ' (' + ' '.join(essayes) + ') : rien chez Yahoo')
            ecrivain_alertes.writerow([cik, ' '.join(essayes), 'aucun cours chez Yahoo'])
        else:
            historiques[cik] = (ticker_utilise, historique)
            if compteur % 50 == 0:
                print(str(compteur) + '/' + str(len(ciks)))

    resultats = {} # cik -> {annee: ligne de resultat}
    for ligne in lignes:
        cik = ligne['cik']
        ligne['ticker_final'] = ligne['ticker']
        ligne['verifier'] = ''
        ligne['date_cours'] = ''
        ligne['cours_yahoo'] = ''
        ligne['facteur'] = ''
        ligne['prix'] = ''
        ligne['ajustement'] = ''
        ligne['capitalisation'] = ''
        ligne['splits'] = [] # Splits de la source qui fournit le cours (Yahoo ou Tiingo)
        ligne['source_prix'] = ''
        ligne['hist'] = None
        if ticker_principal[cik] == '' and historiques[cik] is None:
            ligne['statut'] = 'ticker_inconnu'
        elif historiques[cik] is None:
            ligne['statut'] = 'ticker_introuvable'
        else:
            ligne['ticker_final'] = historiques[cik][0]
            statut, date_cours, cours_yahoo, facteur, prix = prix_a_la_date(historiques[cik][1], ligne['date_cloture'])
            ligne['statut'] = statut
            ligne['date_cours'] = date_cours
            ligne['cours_yahoo'] = cours_yahoo
            ligne['facteur'] = facteur
            ligne['prix'] = prix
            ligne['splits'] = historiques[cik][1][2]
            ligne['hist'] = historiques[cik][1]
            if statut == 'ok':
                ligne['source_prix'] = 'yahoo'
            if ligne['ticker_final'] != ligne['ticker']:
                ajouter_note(ligne, 'ticker de secours ' + ligne['ticker_final'] + ' (principal : ' + ligne['ticker'] + ')')
        if cik in anciens: # Le ticker peut avoir appartenu a une autre societe avant la reorganisation
            ajouter_note(ligne, 'ancien CIK : le cours est celui du ticker actuel')
        if cik not in resultats:
            resultats[cik] = {}
        resultats[cik][ligne['annee']] = ligne

    completer_avec_tiingo(ciks, resultats, ticker_principal, connus, manuels, ecrivain_alertes) # Deuxieme source pour les lignes sans prix Yahoo

    for cik in ciks: # Correction des actions deja apres un split, puis capitalisation et controles
        corriger_unite_des_actions(resultats[cik])
        for annee in resultats[cik]:
            ligne = resultats[cik][annee]
            if ligne['prix'] != '' and ligne['shares'] != '':
                ligne['capitalisation'] = ligne['prix'] * float(ligne['shares'])
        for alerte in lancer_controles(resultats[cik]):
            ecrivain_alertes.writerow([cik, ticker_principal[cik], alerte])
        for annee in resultats[cik]:
            if resultats[cik][annee]['statut'] == 'douteux':
                ecrivain_alertes.writerow([cik, resultats[cik][annee]['ticker_final'], 'ligne ' + str(annee) + ' douteuse : ' + resultats[cik][annee]['verifier']])
    sortie_alertes.close()

    sans_ajuste = 0
    for ligne in lignes: # Cours ajuste et horizons de rendement total, calcules dans la serie qui a fourni le cours de la ligne
        vide = {'cours_ajuste': '', 'date_depart': '', 'ajuste_depart': '', 'date_h1': '', 'ajuste_h1': '', 'date_h3': '', 'ajuste_h3': ''}
        if ligne['statut'] == 'ok' and ligne['hist'] is not None:
            vide = rendement_total(ligne['hist'], ligne)
            if vide['ajuste_depart'] == '':
                sans_ajuste = sans_ajuste + 1
        ligne.update(vide)
    print('Lignes ok sans cours ajuste ou sans date de depart : ' + str(sans_ajuste))

    sortie = open(chemin_sortie, 'w', newline='', encoding='utf-8')
    ecrivain = csv.writer(sortie)
    ecrivain.writerow(['cik', 'annee', 'ticker', 'categorie', 'date_cloture', 'date_cours', 'cours_yahoo', 'facteur_splits', 'prix_epoque', 'shares', 'capitalisation', 'statut', 'verifier', 'ajustement_actions', 'source_prix', 'cours_ajuste', 'date_depot', 'date_depart', 'ajuste_depart', 'date_h1', 'ajuste_h1', 'date_h3', 'ajuste_h3'])
    comptes = {}
    for ligne in lignes:
        ecrivain.writerow([ligne['cik'], ligne['annee'], ligne['ticker_final'], ligne['categorie'], ligne['date_cloture'].isoformat(), ligne['date_cours'],
                           ligne['cours_yahoo'], ligne['facteur'], ligne['prix'], ligne['shares'], ligne['capitalisation'], ligne['statut'], ligne['verifier'], ligne['ajustement'], ligne['source_prix'],
                           ligne['cours_ajuste'], ligne['date_depot'], ligne['date_depart'], ligne['ajuste_depart'], ligne['date_h1'], ligne['ajuste_h1'], ligne['date_h3'], ligne['ajuste_h3']])
        comptes[ligne['statut']] = comptes.get(ligne['statut'], 0) + 1
    sortie.close()
    return comptes

if __name__ == '__main__':
    comptes = ecrire_prix('fondamentaux_sp500.csv', 'cik_categorie.csv', 'ticker_cik_sp500.csv', 'prix_cloture.csv', 'alertes_prix.csv')
    print(comptes)
