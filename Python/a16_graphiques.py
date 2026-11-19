"""a16_graphiques.py : regenere graphique_test_A.png et graphique_test_B.png (racine du projet).
Entrees : backtest_lignes.csv (test A, produit par a14 ; non publie) et backtest_B_annees.csv (test B).
Lancer depuis le dossier Python : py a16_graphiques.py
Script sans fonction : nuage de points g implicite / croissance reelle (test A), puis barres de l'ecart Q1 - Q4 par annee (test B).
"""

import os
import sys
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

X_MIN, X_MAX = -20, 30    # g implicite, en % : points ramenes au bord au-dela (affichage seulement)
Y_MIN, Y_MAX = -50, 100   # croissance reelle du FCFF, en % : idem
SORTIE = os.path.join('..')

for nom in ('backtest_lignes.csv', 'backtest_B_annees.csv'):
    if not os.path.exists(nom):
        sys.exit('a16 : ' + nom + ' absent (relancer a14, voir README)')

# Test A : un point = une societe membre du S&P 500 pour une annee
d = pd.read_csv('backtest_lignes.csv')
m = d[(d['membre'] == True) & d['g_reel'].notna()]
x = (m['g_implicite'] * 100).clip(X_MIN, X_MAX)
y = (m['g_reel'] * 100).clip(Y_MIN, Y_MAX)
fig, ax = plt.subplots(figsize=(7, 5), dpi=130)
ax.scatter(x, y, s=6, alpha=0.3, color='#3a6ea5', edgecolors='none')
ax.plot([X_MIN, X_MAX], [X_MIN, X_MAX], 'k--', linewidth=0.8, label='g réel = g implicite')
ax.set_xlabel('g implicite (WACC), %')
ax.set_ylabel('croissance réelle du FCFF, %')
ax.set_title('Test A, membres S&P 500 (n=' + str(len(m)) + ')')
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(SORTIE, 'graphique_test_A.png'))
plt.close(fig)

# Test B : ecart Q1 - Q4 du rendement en exces a 1 an, par annee, membres
b = pd.read_csv('backtest_B_annees.csv')
b = b[(b['univers'] == 'membres') & (b['horizon'] == '1an')].sort_values('annee')
valeurs = b['ecart_Q1_moins_Q4'] * 100
fig, ax = plt.subplots(figsize=(9, 5.1), dpi=100)
ax.bar(b['annee'], valeurs, color=['#3a8c5f' if v >= 0 else '#b34a42' for v in valeurs], width=0.8)
ax.axhline(0, color='black', linewidth=1)
ax.set_ylabel('Q1 − Q4, points d\'excès à 1 an (rendement total)')
ax.set_title('Test B, membres S&P 500, par année')
fig.tight_layout()
fig.savefig(os.path.join(SORTIE, 'graphique_test_B.png'))
plt.close(fig)
print('graphiques ecrits : n test A =', len(m), '| annees test B =', len(b))
