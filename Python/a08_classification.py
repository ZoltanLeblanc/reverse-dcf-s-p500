"""Table de correspondance code SIC -> categorie (Standard, Banque, Assurance, Fonciere, Cyclique, Non applicable).
Regles : (sic_min, sic_max, categorie, a_verifier). La premiere regle qui correspond gagne.
Codes SIC ecrits de memoire : a verifier sur quelques entreprises.
Pas de fichier lu ni ecrit.
Fonctions principales :
- lire_sic : convertit un texte en code SIC entier, ou None.
- categorie_depuis_sic : renvoie (categorie, a_verifier, source) pour un code SIC."""
REGLES_SIC = [
    (6770, 6770, 'Non applicable', 'non'),   # societes cheques en blanc (SPAC)
    (6189, 6189, 'Non applicable', 'non'),   # vehicules de titrisation
    (6798, 6798, 'Fonciere', 'oui'),         # REIT : a separer en classique / hypothecaire
    (6021, 6029, 'Banque', 'non'),           # banques commerciales
    (6035, 6036, 'Banque', 'non'),           # caisses d'epargne
    (6099, 6099, 'Standard', 'oui'),         # fonctions liees aux depots (paiements)
    (6111, 6111, 'Banque', 'non'),           # agences de credit federales
    (6141, 6141, 'Banque', 'non'),           # credit a la consommation
    (6153, 6153, 'Banque', 'non'),           # credit aux entreprises court terme
    (6159, 6162, 'Banque', 'non'),           # credit divers et prets hypothecaires
    (6172, 6172, 'Banque', 'non'),           # credit-bail
    (6199, 6199, 'Banque', 'oui'),           # services financiers divers
    (6200, 6200, 'Standard', 'non'),         # bourses et courtiers de matieres
    (6211, 6211, 'Banque', 'oui'),           # courtiers et banques d'investissement
    (6282, 6282, 'Standard', 'non'),         # gestionnaires d'actifs
    (6311, 6311, 'Assurance', 'non'),        # assurance vie
    (6321, 6321, 'Assurance', 'non'),        # assurance accident et sante
    (6324, 6324, 'Assurance', 'non'),        # sante geree : OCF gonfle par les primes encaissees d'avance
    (6331, 6331, 'Assurance', 'non'),        # assurance dommages
    (6351, 6361, 'Assurance', 'non'),        # caution et titres de propriete
    (6399, 6399, 'Assurance', 'non'),        # autres assureurs
    (6411, 6411, 'Standard', 'non'),         # courtiers en assurance
    (6500, 6599, 'Standard', 'oui'),         # immobilier hors REIT
    (4911, 4911, 'Regulee', 'oui'),          # electricite : producteurs non regules = cycliques
    (4922, 4924, 'Regulee', 'oui'),          # gaz : transport et distribution
    (4931, 4932, 'Regulee', 'non'),          # services combines electricite et gaz
    (4941, 4941, 'Regulee', 'non'),          # eau
    (1000, 1499, 'Cyclique', 'non'),         # mines, petrole et gaz, services petroliers
    (2600, 2631, 'Cyclique', 'non'),         # papier
    (2900, 2999, 'Cyclique', 'non'),         # raffinage
    (3310, 3390, 'Cyclique', 'non'),         # acier et metaux
    (4512, 4512, 'Cyclique', 'non'),         # compagnies aeriennes
]

def lire_sic(valeur): # Convertit le texte lu en entier, ou None si vide ou invalide
    texte = str(valeur).strip()
    if texte == '':
        return None
    try:
        return int(float(texte))
    except ValueError:
        return None

def categorie_depuis_sic(sic): # Renvoie (categorie, a_verifier, source) pour un code SIC
    if sic is None:
        return 'Non applicable', 'non', 'sic manquant'
    for sic_min, sic_max, categorie, a_verifier in REGLES_SIC:
        if sic_min <= sic <= sic_max:
            return categorie, a_verifier, 'regle sic'
    return 'Standard', 'non', 'defaut'
