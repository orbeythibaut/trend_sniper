# src/trend_sniper/visualization.py
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import Optional, Dict
from .strategies import BaseStrategy, TrendStrategy, SniperStrategy
from .indicators import calc_atr


class StrategyPlotter:
    """Visualisations individuelles par stratégie (debug / analyse unitaire)."""

    def __init__(self, strategy: BaseStrategy) -> None:
        self.strategy = strategy
        self.asset_ticker = strategy.asset.ticker
        if not self.strategy.equity_curve:
            raise ValueError("Lancez .run() avant de tracer les graphiques.")

    def _prepare_data(self) -> pd.DataFrame:
        df = self.strategy.signals.copy()
        df['Equity_Curve'] = self.strategy.equity_curve
        df['Position'] = self.strategy.positions
        return df

    def plot_performance(self, save_path: Optional[str] = None) -> None:
        """Equity Curve vs Prix de l'actif."""
        df = self._prepare_data()
        fig, ax1 = plt.subplots(figsize=(12, 6))
        ax1.plot(df.index, df['Close'], color='blue', label=f'Price {self.asset_ticker}', alpha=0.6)
        ax1.set_ylabel(f'Price {self.asset_ticker}', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')
        ax2 = ax1.twinx()
        ax2.plot(df.index, df['Equity_Curve'], color='green', label='Equity Curve', linewidth=2)
        ax2.set_ylabel('Equity Curve ($)', color='green')
        ax2.tick_params(axis='y', labelcolor='green')
        plt.title(f'Backtest {self.asset_ticker} — {type(self.strategy).__name__}')
        plt.grid(True, linestyle='--', linewidth=0.5)
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()

    def plot_trend_debug(self) -> None:
        """Prix vs Indicateur Donchian (Close-based, comme le script original)."""
        if not isinstance(self.strategy, TrendStrategy):
            print("[WARN] plot_trend_debug est réservé à TrendStrategy.")
            return
        df = self.strategy.signals
        plt.figure(figsize=(12, 6))
        plt.plot(df.index, df['Close'], color='black', label='Close Price', alpha=0.7)
        plt.plot(df.index, df['Max_Indicator'], color='red', linestyle='--', label='Donchian Max Close (20d)')
        plt.title(f'Signaux Trend sur {self.asset_ticker}')
        plt.ylabel('Price ($)')
        plt.legend()
        plt.grid(True)
        plt.show()

    def plot_sniper_debug(self) -> None:
        """Prix vs Bande Bollinger haute + Bandwidth (comme le script original)."""
        if not isinstance(self.strategy, SniperStrategy):
            print("[WARN] plot_sniper_debug est réservé à SniperStrategy.")
            return
        df = self.strategy.signals
        bandwidth_threshold = df['Bandwidth'].quantile(0.20)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        ax1.plot(df.index, df['Close'], color='black', label='Close Price', alpha=0.8)
        ax1.plot(df.index, df['Upper'], color='blue', linestyle='--', label='Upper Bollinger Band')
        ax1.set_title(f'Signaux Sniper sur {self.asset_ticker}')
        ax1.set_ylabel('Price ($)')
        ax1.legend()
        ax1.grid(True)
        ax2.plot(df.index, df['Bandwidth'], color='purple', label='BB Bandwidth')
        ax2.axhline(y=bandwidth_threshold, color='red', linestyle='--',
                    label=f'Threshold P20 = {bandwidth_threshold:.3f}')
        ax2.set_ylabel('Bandwidth')
        ax2.legend()
        ax2.grid(True)
        plt.tight_layout()
        plt.show()


class PortfolioReport:
    """
    Rapport complet du portefeuille hybride (Trend + Sniper vs S&P 500).
    Reproduit fidèlement les métriques et graphiques du script original.
    """

    def __init__(
        self,
        equity_trend: pd.Series,
        equity_sniper: pd.Series,
        sp500: pd.Series,
        assets_ohlcv: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> None:
        # Alignement sur l'intersection des dates
        common_idx = equity_trend.index.intersection(equity_sniper.index)
        self.equity_trend = equity_trend.reindex(common_idx).astype(float).dropna()
        self.equity_sniper = equity_sniper.reindex(common_idx).astype(float).dropna()
        # Ré-alignement après dropna pour garder un index commun non vide
        common_idx = self.equity_trend.index.intersection(self.equity_sniper.index)
        self.equity_trend = self.equity_trend.reindex(common_idx)
        self.equity_sniper = self.equity_sniper.reindex(common_idx)
        self.equity_global = self.equity_trend + self.equity_sniper

        sp500_aligned = sp500.reindex(common_idx).ffill()
        if sp500_aligned.empty:
            raise ValueError("La série S&P 500 est vide sur l'intervalle d'intersection des stratégies.")
        self.benchmark = sp500_aligned / sp500_aligned.iloc[0] * self.equity_global.iloc[0]

        # Garde-fous : prévenir les graphiques/plots vides
        if len(self.equity_global.dropna()) == 0:
            raise ValueError(
                "Aucune donnée disponible après alignement des dates.\n"
                "- Vérifiez que chaque ticker possède des données sur la plage choisie (ex: HOOD après 2021-07-29).\n"
                "- Ajustez start_date ou remplacez le ticker manquant."
            )

        self.assets_ohlcv = assets_ohlcv or {}

    def _get_metrics(self, equity: pd.Series) -> dict:
        returns = equity.pct_change().fillna(0)
        start_cap, end_cap = equity.iloc[0], equity.iloc[-1]
        total_return = (end_cap / start_cap) - 1
        years = (equity.index[-1] - equity.index[0]).days / 365.25
        cagr = (end_cap / start_cap) ** (1 / years) - 1 if years > 0 else 0
        volatility = returns.std() * np.sqrt(252)
        sharpe = (cagr - 0.04) / volatility if volatility > 0 else 0
        rolling_max = equity.cummax()
        max_dd = ((equity - rolling_max) / rolling_max).min()
        calmar = cagr / abs(max_dd) if max_dd != 0 else 0
        exposure = returns[returns != 0].count() / len(returns)
        return {
            "Capital Final ($)": round(end_cap, 2),
            "Total Return (%)": round(total_return * 100, 2),
            "CAGR (%)": round(cagr * 100, 2),
            "Volatilité An. (%)": round(volatility * 100, 2),
            "Max Drawdown (%)": round(max_dd * 100, 2),
            "Sharpe Ratio": round(sharpe, 3),
            "Calmar Ratio": round(calmar, 3),
            "Exposition Marché (%)": round(exposure * 100, 1),
        }

    def print_metrics_table(self) -> pd.DataFrame:
        """Tableau de performance complet (comme get_advanced_metrics du script original)."""
        df = pd.DataFrame(
            [
                self._get_metrics(self.equity_trend),
                self._get_metrics(self.equity_sniper),
                self._get_metrics(self.equity_global),
                self._get_metrics(self.benchmark),
            ],
            index=['Trend (TSLA+HOOD)', 'Sniper (PLTR)', 'Global Hybride', 'S&P 500'],
        )
        print("\n RAPPORT DE PERFORMANCE ")
        print("-" * 60)
        # Transposé : métriques en lignes, stratégies en colonnes → lisible sans troncature
        with pd.option_context('display.max_rows', None, 'display.max_columns', None,
                               'display.width', None):
            print(df.T)
        return df

    def print_atr_table(self) -> Optional[pd.DataFrame]:
        """Tableau ATR comme dans le rapport PDF (critère de sélection des actifs)."""
        if not self.assets_ohlcv:
            print("[WARN] Passez assets_ohlcv à PortfolioReport pour calculer l'ATR.")
            return None
        classifications = {
            'TSLA': 'Haute Volatilité / Directionnel',
            'HOOD': 'Hyper-Volatilité / Beta Élevé',
            'PLTR': 'Fat Tails / Bruit Élevé',
            '^GSPC': 'Référence Marché (SPY)',
        }
        rows = []
        for ticker, df in self.assets_ohlcv.items():
            if not all(c in df.columns for c in ['High', 'Low', 'Close']):
                continue
            atr = calc_atr(df, window=14).dropna()
            atr_abs = round(atr.mean(), 2)
            atr_pct = round((atr / df['Close'].reindex(atr.index)).mean() * 100, 2)
            rows.append({
                'Actif': ticker,
                'ATR Absolu Moy. ($)': atr_abs,
                'ATR Relatif Moy. (%)': atr_pct,
                'Classification': classifications.get(ticker, '-'),
            })
        df_atr = pd.DataFrame(rows).set_index('Actif')
        print("\n ANALYSE ATR — Critère de Sélection des Actifs ")
        print("-" * 60)
        print(df_atr)
        return df_atr

    def plot(self, print_tables: bool = True) -> None:
        """
        Graphique 2 panneaux identique au script original :
        - Panel haut  : Wealth Curves (Global, Trend, Sniper, S&P 500)
        - Panel bas   : Volatilité roulante 30j annualisée
        + Verdict automatique basé sur le Calmar Ratio
        """
        if print_tables:
            # Imprime les métriques avant les graphiques pour les sessions REPL / notebooks
            self.print_atr_table()
            self.print_metrics_table()

        vol_trend = self.equity_trend.pct_change().rolling(30).std() * np.sqrt(252)
        vol_sniper = self.equity_sniper.pct_change().rolling(30).std() * np.sqrt(252)
        vol_global = self.equity_global.pct_change().rolling(30).std() * np.sqrt(252)

        plt.style.use('seaborn-v0_8-darkgrid')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10),
                                        gridspec_kw={'height_ratios': [2, 1]})

        ax1.plot(self.equity_global, color='black', linewidth=2,
                 label='Global Hybride (Trend x Sniper)')
        ax1.plot(self.equity_trend, color='blue', alpha=0.5, linestyle='--',
                 label='Trend Only (TSLA+HOOD)')
        ax1.plot(self.equity_sniper, color='orange', alpha=0.5, linestyle='--',
                 label='Sniper Only (PLTR)')
        ax1.plot(self.benchmark, color='red', alpha=0.4, label='S&P 500')
        ax1.set_title('Performance Comparée (Wealth Curve)', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Capital ($)')
        ax1.legend(loc='upper left')

        ax2.plot(vol_global, color='black', linewidth=1.5, label='Volatilité Globale')
        ax2.plot(vol_sniper, color='orange', alpha=0.4, label='Volatilité Sniper (PLTR)')
        ax2.plot(vol_trend, color='blue', alpha=0.4, label='Volatilité Trend')
        ax2.set_title('Analyse du Risque : Volatilité Roulante (30j)', fontsize=12)
        ax2.set_ylabel('Volatilité An.')
        ax2.legend()

        calmar = self._get_metrics(self.equity_global)['Calmar Ratio']
        print("\n VERDICT :")
        print(f"Votre Ratio de Calmar Global est de {calmar}.")
        if calmar > 1.5:
            print(">> EXCELLENT. Pour chaque dollar de risque (drawdown), vous gagnez 1.5$ de rendement.")
            print(">> La stratégie Sniper (faible win rate) est compensée par la robustesse du Trend.")
        elif calmar > 0.5:
            print(">> CORRECT, mais perfectible. La volatilité du Sniper pèse peut-être trop lourd.")
        else:
            print(">> INSUFFISANT. Le risque de ruine (Drawdown) est trop élevé par rapport aux gains.")

        import sys
        sys.stdout.flush()
        plt.tight_layout()
        # Non‑blocking show to avoid “hang until window close” in VS Code / REPL
        plt.show(block=False)
        plt.pause(0.1)
