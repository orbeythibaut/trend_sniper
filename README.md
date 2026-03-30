# Trend Sniper : Analyse Quantitative & Backtesting 🚀

Ce projet est une plateforme de backtesting développée en Python, conçue pour analyser et valider des stratégies de trading hybrides sur des actifs technologiques à haute volatilité (TSLA, PLTR, HOOD). 

L'objectif est de démontrer qu'un portefeuille combinant le suivi de tendance (**Trend**) et la capture d'événements extrêmes (**Sniper/Fat-Tails**) permet d'optimiser le ratio de Calmar et la convexité globale du portefeuille.

## 🧠 Stratégies Implémentées

Le projet segmente l'univers d'investissement en deux clusters distincts:

1.  **Stratégie Trend (Suivi de Tendance)** : Basée sur les cassures de canaux de Donchian (20 jours). Elle vise à capturer le momentum moyen terme avec une gestion stricte du risque via un Stop-Loss et un Break-Even actif.
2.  **Stratégie Sniper (Fat-Tail Hunter)** : Exploite les phases de compression de volatilité (Bollinger Band Squeeze). Elle cherche à capturer des mouvements explosifs ("Cygnes Noirs") en acceptant un taux de réussite plus faible en échange d'une asymétrie positive massive.

## 🛠️ Architecture Technique

Conformément aux principes de génie logiciel enseignés en cours, le projet adopte une structure modulaire et orientée objet (POO) :

* **`PriceSeries`** : Classe de base encapsulant les séries temporelles et les calculs de rendements (log et linéaires).
* **`Asset`** : Représentation d'un actif financier utilisant le pattern de **Composition** sur une `PriceSeries`.
* **`DataLoader`** : Système de récupération de données (API Yahoo Finance) avec un **système de cache avancé** gérant 5 scénarios de chevauchement temporel pour optimiser les performances.
* **`BaseStrategy`** : Architecture d'héritage pour les moteurs de backtest, permettant une gestion standardisée de l'équité et de la comptabilité des positions.
* **`StrategyPlotter`** : Module de visualisation dédié pour l'analyse des courbes de richesse et de la volatilité roulante.

## 🚀 Installation & Utilisation

Le projet utilise `uv` pour la gestion des dépendances et de l'environnement virtuel.

### Installation
```bash
# Cloner le repository
git clone [https://github.com/orbeythibaut/trend_sniper.git](https://github.com/orbeythibaut/trend_sniper.git)
cd trend_sniper

# Créer l'environnement et installer les dépendances
uv venv
source .venv/bin/activate  # ou .venv\Scripts\activate sur Windows
uv pip install -e .
 
##Run cette consigne dans le REPL/TERMINAL pour lancer le code et le test
import sys, os, pandas as pd
sys.path.insert(0, os.path.abspath("src"))

from trend_sniper import DataLoader, Asset, run_full_report
from trend_sniper.strategies import TrendStrategy, SniperStrategy

start_date, end_date = "2021-08-01", "2025-12-31"  # after HOOD IPO
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
    show_plots=True,  # tables first, plots non-blocking
)


