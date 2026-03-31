# Trend Sniper — Analyse Quantitative & Backtesting de Stratégies Asymétriques

**Auteurs :** Thibaut Orbey & Groupe de Projet
**Institution :** Université Paris Dauphine — Cours de Python Appliqué à la Finance (R. Schwartz)
**Période d'Analyse :** 2021–2025

---

## Lancement du Backtesting

Exécuter le bloc suivant dans un REPL Python ou terminal depuis la racine du projet :

```python
import sys, os, pandas as pd
sys.path.insert(0, os.path.abspath("src"))

from trend_sniper import DataLoader, Asset, run_full_report
from trend_sniper.strategies import TrendStrategy, SniperStrategy

start_date, end_date = "2021-08-01", "2025-12-31"  # Post-IPO HOOD
dl = DataLoader(cache_dir=".cache_demo")

raw_tsla = dl.fetch_data("TSLA", start=start_date, end=end_date)
raw_hood = dl.fetch_data("HOOD", start=start_date, end=end_date)
raw_pltr = dl.fetch_data("PLTR", start=start_date, end=end_date)
raw_gspc = dl.fetch_data("^GSPC", start=start_date, end=end_date)

trend_tsla = TrendStrategy(Asset("TSLA", raw_tsla)); trend_tsla.run()
trend_hood = TrendStrategy(Asset("HOOD", raw_hood)); trend_hood.run()
sniper_pltr = SniperStrategy(Asset("PLTR", raw_pltr)); sniper_pltr.run()

equity_tsla   = pd.Series(trend_tsla.equity_curve, index=trend_tsla.signals.index)
equity_hood   = pd.Series(trend_hood.equity_curve, index=trend_hood.signals.index)
equity_sniper = pd.Series(sniper_pltr.equity_curve, index=sniper_pltr.signals.index)
common_idx    = equity_tsla.index.intersection(equity_hood.index)
equity_trend  = equity_tsla.reindex(common_idx) + equity_hood.reindex(common_idx)

report = run_full_report(
    equity_trend=equity_trend,
    equity_sniper=equity_sniper,
    sp500=raw_gspc["Close"],
    assets_ohlcv={"TSLA": raw_tsla, "HOOD": raw_hood, "PLTR": raw_pltr, "^GSPC": raw_gspc},
    show_plots=True,
)
```

---

## 1. Résumé Exécutif

Ce projet de recherche implémente une plateforme de backtesting vectorisée et modulaire visant à valider une thèse de gestion asymétrique (*Convexity Trading*). Contrairement à l'intuition du trading discrétionnaire, l'objectif de ce système algorithmique n'est pas de maximiser la probabilité de gain (*Win Rate*), mais l'espérance mathématique globale en exploitant la structure de volatilité d'actifs technologiques à forte capitalisation.

En segmentant l'univers d'investissement selon des signatures statistiques précises — autocorrélation sérielle positive versus kurtosis élevée — nous démontrons qu'une diversification par *style de trading* (Trend-Following couplé à une stratégie *Fat-Tail Hunter*) permet d'optimiser le ratio de Calmar et de capturer des événements de queue de distribution structurellement inaccessibles aux gestions directionnelles traditionnelles.

---

## 2. Cadre Théorique : L'Approche de Harvey (2019)

Le cadre conceptuel de ce portefeuille hybride s'appuie sur la littérature académique relative à la gestion des risques extrêmes, notamment les travaux de Harvey *et al.* (2019) dans *"The Best of Strategies for the Worst of Times"*. La thèse centrale postule que la diversification par classe d'actifs devient inopérante lors de chocs systémiques, les corrélations inter-actifs convergeant vers 1 en phase de stress.

Pour pallier ce risque de corrélation endogène, l'architecture combine deux moteurs de performance structurellement décorrélés :

- **Trend Following** — Exploite l'autocorrélation positive sérielle pour générer du rendement lors de marchés directionnels persistants ou de crises lentes à déploiement graduel.
- **Tail Risk / Sniper** — Exploite les phases de compression de volatilité pour capturer des sauts de prix violents (*Cygnes Noirs*). Cette composante agit comme un stabilisateur de convexité du portefeuille global, offrant des rendements asymétriques massifs qui compensent son faible taux de réussite structurel (*cost of carry*).

---

## 3. Définition de l'Univers et Clustering (Critère ATR)

Un système de suivi de tendance doit surmonter un *hurdle rate* implicite — coûts de friction, slippage, faux signaux — avant toute génération d'alpha net. Par conséquent, l'univers est restreint aux actifs présentant un Average True Range (ATR) relatif supérieur à **4 %**.

L'ATR est défini comme la volatilité absolue moyenne sur $n$ périodes :

$$ATR = \frac{1}{n} \sum_{i=1}^{n} \max\!\left(H_i - L_i,\; |H_i - C_{i-1}|,\; |L_i - C_{i-1}|\right)$$

### Matrice de Sélection Empirique (Moyennes 2021–2025)

| Actif  | ATR Absolu Moy. ($) | Signature Statistique                          | Classification Algorithmique |
|--------|---------------------|------------------------------------------------|------------------------------|
| TSLA   | 13,54               | Autocorrélation positive / Bêta élevé          | Stratégie Trend              |
| HOOD   | 1,94                | Autocorrélation positive / Hyper-volatilité    | Stratégie Trend              |
| PLTR   | 2,37                | Kurtosis élevée / Bruit stochastique fort      | Stratégie Sniper             |
| ^GSPC  | 64,55               | Faible volatilité relative                     | Benchmark (S&P 500)          |

**Justification du clustering :** bien que TSLA, HOOD et PLTR partagent des ATR relatifs comparables, leurs distributions de rendements diffèrent structurellement. TSLA et HOOD présentent des tendances persistantes justifiant un mécanisme de *Break-Even* actif. PLTR, dominé par le bruit intra-journalier et une forte kurtosis, impose au contraire l'absence de Break-Even afin de maintenir l'exposition lors de la phase de *shakeout* précédant l'impulsion directionnelle.

---

## 4. Méthodologie Algorithmique

### 4.1 Moteur Alpha — Trend Following

- **Signal d'entrée :** cassure haussière du Canal de Donchian à 20 jours (cycle psychologique mensuel).
- **Gestion des risques :** Stop-Loss rigide à −4 %. Un Break-Even actif est déclenché à +4 % (1R) : un retour au niveau d'entrée sur un actif censé être en régime tendanciel invalide la thèse directionnelle et justifie une sortie *flat*.

### 4.2 Moteur Bêta/Convexité — Sniper / Fat-Tail Hunter

- **Signal d'entrée :** compression des Bandes de Bollinger (Bandwidth inférieure au 20ème percentile) suivie d'une cassure de la bande supérieure. La volatilité étant cyclique par nature, cette compression précède mécaniquement l'expansion.
- **Gestion des risques :** Stop-Loss élargi à −15 % pour absorber le bruit stochastique. Le Break-Even est strictement interdit afin de garantir la participation intégrale à la queue de distribution lors de l'événement de queue.

---

## 5. Architecture Logicielle

Afin de répondre aux exigences de scalabilité, de testabilité et de reproductibilité propres à la recherche quantitative, le code est structuré selon les paradigmes de la Programmation Orientée Objet (POO) :

- **Modularité & Héritage** — Séparation stricte de la logique de calcul (`indicators.py`), de la gestion des données (`dataloader.py`) et des moteurs d'exécution (`strategies.py` héritant d'une `BaseStrategy` abstraite).
- **Système de cache intelligent** — Module de gestion des requêtes de séries temporelles avec résolution des chevauchements de dates (Exact, Contains, Overlap Before/After, Miss) pour minimiser les appels redondants à l'API Yahoo Finance.
- **Type Hinting & CI/CD** — Code typé conformément aux standards PEP 8 ; développement versionné sous Git en mode collaboratif.

---

## 6. Analyse de Performance (2021–2025)

*Capital initial normalisé. Taux sans risque estimé à 4,0 %.*

| Indicateur Financier          | Trend (TSLA+HOOD) | Sniper (PLTR) | Global Hybride | S&P 500    |
|-------------------------------|-------------------|---------------|----------------|------------|
| Capital Final ($)             | 60 973,10         | 57 547,08     | 118 520,19     | 60 910,22  |
| Total Return (%)              | 204,87            | 187,74        | 196,30         | 52,28      |
| CAGR (%)                      | 29,33             | 27,62         | 28,48          | 10,19      |
| Volatilité Annualisée (%)     | 23,44             | 35,28         | 21,58          | 17,51      |
| Max Drawdown (%)              | −29,66            | −49,71        | −30,82         | −25,43     |
| Sharpe Ratio                  | 1,081             | 0,669         | **1,134**      | 0,353      |
| Calmar Ratio                  | 0,989             | 0,555         | 0,924          | 0,401      |
| Exposition Marché (%)         | 44,10             | 35,90         | 60,50          | 99,90      |

---

## 7. Discussion Critique et Verdict

L'analyse des résultats confirme la validité de la thèse de diversification par méthode. Le portefeuille Global Hybride affiche un Sharpe Ratio de **1,134**, démontrant une génération d'alpha significative par rapport au benchmark (0,353). La combinaison des deux moteurs permet par ailleurs de réduire la volatilité globale (21,58 %) par rapport au moteur Sniper isolé (35,28 %), illustrant l'effet de diversification structurelle recherché.

**Verdict et limites du modèle :** le Calmar Ratio global s'établit à 0,924 — résultat jugé satisfaisant mais perfectible. Le drawdown sévère du moteur Sniper (−49,71 %) dégrade le profil de risque global et met en lumière la difficulté inhérente à la capture de *Fat Tails* : un Win Rate structurellement faible génère un coût psychologique et financier (*saignement* du capital) difficilement soutenable en gestion discrétionnaire.

**L'automatisation absolue constitue par conséquent une exigence mathématique**, permettant de s'affranchir des biais cognitifs et de garantir la présence sur le marché lors de l'apparition du Cygne Noir. Une itération future du modèle devra intégrer un filtre de régime de volatilité — par exemple le VIX Index — afin de désactiver dynamiquement le moteur Sniper lors des phases de compression macroéconomique défavorables.

---

*Research Note — Usage Académique. Les performances passées ne préjugent pas des performances futures.*
