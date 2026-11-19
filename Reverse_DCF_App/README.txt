REVERSE DCF S&P 500 : application d'exploration (hors ligne)

OUVRIR   : d'abord generer les donnees (py build_data.py, voir ci-dessous ; data\data.js n'est pas publie), puis double-clique sur index.html
           (Chrome, Edge ou Firefox). Aucun serveur.
METTRE A JOUR : si tu relances un script a06-a15 et que les CSV de ..\Python changent,
                double-clique sur mettre_a_jour.bat (ou : py build_data.py). Cela regenere data\data.js.
PAGES    : Accueil, Entreprise (calcul de g etape par etape), Marche, Blocs, Backtest, Qualite, Methode.
CURSEUR  : en haut de chaque page, la prime de risque (5 % par defaut). Le taux r est un WACC de marche par annee
           (taux 10 ans a la date de cloture + prime, pondere avec la dette), cycliques +1 pt. La case "r fixe 9 %" remet l'ancienne methode.
UNIVERS  : page Backtest, choix entre membres du S&P 500 a la date (reference), hors indice, toutes les societes.
FCFF     : OCF + interets apres impot - capex.

Dossiers : css/ (style), js/ (01 coeur et formules, 02 graphiques, 03-05 pages, 06 navigation), data/data.js (donnees fusionnees).
Source des donnees : les CSV du dossier Python (prix_cloture, fondamentaux, valeur_entreprise, g_implicite, backtest_lignes, secteur...).
Non publies (licences des donnees, voir README racine) : tiingo_token.txt, Companyfacts, Prix, CSV de prix, data.js.
