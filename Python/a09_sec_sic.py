"""Recupere le code SIC d'une entreprise (par CIK) via l'API submissions de la SEC, avec cache local.
Entree : API data.sec.gov (User-Agent obligatoire, voir a03_sec_api). Sortie : fichiers SICxxxxxxxxxx.json dans le dossier Submissions.
Fonctions principales :
- construire_url_submissions : url de l'API submissions pour un CIK.
- construire_chemin_cache_sic : chemin du fichier de cache (sic et description seulement).
- obtenir_sic_entreprise : renvoie {'sic', 'description'} depuis le cache ou la SEC, None si introuvable."""
import requests
import json
import os
import time
from a03_sec_api import MON_USER_AGENT
from a03_sec_api import DELAI_ENTRE_REQUETES
from a03_sec_api import RACINE
from a03_sec_api import verifier_user_agent

DOSSIER_SIC = os.environ.get("DOSSIER_SUBMISSIONS", os.path.join(RACINE, "Submissions"))

def construire_url_submissions(cik): # Url de l'API submissions de la SEC pour un CIK
    cik_avec_zeros = cik.zfill(10)
    url = "https://data.sec.gov/submissions/CIK" + cik_avec_zeros + ".json"
    return url

def construire_chemin_cache_sic(cik): # Chemin du petit fichier de cache (sic seulement)
    nom_fichier = "SIC" + cik.zfill(10) + ".json"
    return os.path.join(DOSSIER_SIC, nom_fichier)

def obtenir_sic_entreprise(cik): # Renvoie {'sic':..., 'description':...} depuis le cache ou la SEC, None si introuvable
    chemin_cache = construire_chemin_cache_sic(cik)

    if os.path.exists(chemin_cache):
        fichier = open(chemin_cache, 'r', encoding='utf-8')
        try:
            resultat = json.loads(fichier.read())
            fichier.close()
            return resultat
        except json.JSONDecodeError: # cache tronque : on le retelecharge
            fichier.close()

    if not os.path.exists(DOSSIER_SIC):
        os.makedirs(DOSSIER_SIC)

    verifier_user_agent()
    en_tetes = {"User-Agent": MON_USER_AGENT} # Obligatoire pour la SEC
    reponse = None
    for tentative in range(4): # 429 et 5xx sont transitoires : on attend puis on reessaie (404 : pas de reessai)
        reponse = requests.get(construire_url_submissions(cik), headers=en_tetes, timeout=60)
        time.sleep(DELAI_ENTRE_REQUETES)
        if reponse.status_code != 429 and reponse.status_code < 500:
            break
        time.sleep(30 * (tentative + 1))

    if reponse.status_code != 200:
        print('pas de submissions pour ce cik : ' + cik + ' (code ' + str(reponse.status_code) + ')')
        return None

    donnees = reponse.json()
    resultat = {}
    resultat['sic'] = str(donnees.get('sic', ''))
    resultat['description'] = donnees.get('sicDescription', '')

    fichier = open(chemin_cache + '.tmp', 'w', encoding='utf-8') # On ne garde que le sic, pas tout le json
    fichier.write(json.dumps(resultat))
    fichier.close()
    os.replace(chemin_cache + '.tmp', chemin_cache) # ecriture atomique

    return resultat
