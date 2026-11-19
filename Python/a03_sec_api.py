"""Acces a l'API companyfacts de la SEC avec cache disque.
Entree : API data.sec.gov (variable d'environnement SEC_USER_AGENT obligatoire) ; dossier de cache Companyfacts.
Sortie : un fichier CIK##########.json par entreprise dans le dossier de cache.

Fonctions principales :
- verifier_user_agent : arrete le programme si le User-Agent exige par la SEC est absent.
- construire_url_companyfacts : construit l'URL de l'API pour un CIK.
- construire_chemin_cache : construit le chemin du fichier de cache d'un CIK.
- obtenir_donnees_entreprise : lit le cache ou telecharge (avec reessais), puis renvoie le JSON.
"""
import requests
import json
import os
import time


RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Dossier du projet (parent de Python/)
DOSSIER_CACHE = os.environ.get("DOSSIER_COMPANYFACTS", os.path.join(RACINE, "Companyfacts")) # Surcharge possible par variable d'environnement

MON_USER_AGENT = os.environ.get("SEC_USER_AGENT", "") # Exige par la SEC : "Prenom Nom adresse@exemple.com" (variable d'environnement SEC_USER_AGENT)

def verifier_user_agent(): # A appeler avant tout appel reseau vers la SEC
    if not MON_USER_AGENT:
        raise SystemExit('Definir la variable d\'environnement SEC_USER_AGENT="Prenom Nom adresse@exemple.com" (exige par la SEC)')

DELAI_ENTRE_REQUETES = 0.15

# https://www.sec.gov/search-filings/edgar-application-programming-interfaces
# Each entity’s current filing history is available at the following URL:

# https://data.sec.gov/submissions/CIK##########.json
# Where the ########## is the entity’s 10-digit central index key (CIK), including leading zeros.

# This JSON data structure contains metadata such as current name, former name, and stock exchanges and ticker symbols of publicly-traded companies. The object’s property path contains at least one year’s of filing or to 1,000 (whichever is more) of the most recent filings in a compact columnar data array. If the entity has additional filings, files will contain an array of additional JSON files and the date range for the filings each one contains.

# CIK par entreprises : https://www.sec.gov/search-filings/cik-lookup

def construire_url_companyfacts(cik): # Création de l'url qui permet de chercher les données JSON de chaque dépôt
    cik_avec_zeros = cik.zfill(10) # Rajout de "0" pour que len(cik)=10
    url = "https://data.sec.gov/api/xbrl/companyfacts/CIK" + cik_avec_zeros + ".json"
    return url

def construire_chemin_cache(cik): # Création du chemin de sauvegarde des dépôts
    cik_avec_zeros = cik.zfill(10)
    nom_fichier = "CIK" + cik_avec_zeros + ".json"
    chemin_complet = os.path.join(DOSSIER_CACHE, nom_fichier)
    return chemin_complet

def obtenir_donnees_entreprise(cik): # Décide si on doit vraiment contacter la SEC, ou si on peut lire un fichier déjà sur le disque.
    chemin_cache = construire_chemin_cache(cik)

    if os.path.exists(chemin_cache):
        fichier = open(chemin_cache, "r", encoding="utf-8")
        contenu_texte = fichier.read()
        fichier.close()
        try:
            donnees = json.loads(contenu_texte)
            return donnees
        except json.JSONDecodeError: # cache tronque (arret pendant l'ecriture) : on le retelecharge
            print('cache corrompu pour le cik ' + cik + ' : retelechargement') 

    if not os.path.exists(DOSSIER_CACHE): # Si le dossier de cache n'existe pas encore sur cette machine
        os.makedirs(DOSSIER_CACHE) # On le crée avant d'essayer d'y écrire un fichier, sinon ça plante !!

    url = construire_url_companyfacts(cik)
    verifier_user_agent()
    en_tetes = {"User-Agent": MON_USER_AGENT} # Obligatoire pour la SEC

    reponse = None
    for tentative in range(4): # 429 et 5xx sont transitoires : on attend puis on reessaie (404 : pas de reessai)
        reponse = requests.get(url, headers=en_tetes, timeout=60)
        time.sleep(DELAI_ENTRE_REQUETES)
        if reponse.status_code != 429 and reponse.status_code < 500:
            break
        time.sleep(30 * (tentative + 1))

    if reponse.status_code != 200:
        print('aucune donnee disponible pour ce cik : ' + cik + ' (code ' + str(reponse.status_code) + ')')
        return None

    donnees = reponse.json() # Transforme directement la réponse HTTP en dictionnaire Python
    
    fichier = open(chemin_cache + ".tmp", "w", encoding="utf-8")
    fichier.write(json.dumps(donnees)) # On sauvegarde ce qu'on vient de télécharger, pour ne plus jamais le retélécharger
    fichier.close()
    os.replace(chemin_cache + ".tmp", chemin_cache) # ecriture atomique : jamais de JSON tronque

    return donnees
    
 