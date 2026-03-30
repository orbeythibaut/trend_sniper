# src/trend_sniper/strategies.py
import pandas as pd
import numpy as np
from typing import List
from .asset import Asset
from .indicators import calc_donchian_channel, calc_bollinger_bands

class BaseStrategy:
    """
    Classe mère abstraite pour les moteurs de backtest.
    Gère la comptabilité commune.
    """
    def __init__(self, asset: Asset, initial_capital: float) -> None:
        self.asset = asset
        self.initial_capital = initial_capital

        # Résultats du backtest
        self.equity_curve: List[float] = []
        self.positions: List[float] = []
        self.cash_history: List[float] = []
        self.signals = pd.DataFrame()

    def run(self) -> None:
        """Méthode principale à redéfinir dans les classes filles."""
        raise NotImplementedError("Cette méthode doit être implémentée par l'enfant.")


class TrendStrategy(BaseStrategy):
    """
    Moteur de stratégie Donchian Channel Breakout (Trend Following).
    Identique au script original : Donchian sur Close, SL/TP/Break-Even.
    """
    def __init__(self, asset: Asset, initial_capital: float = 10000.0,
                 window: int = 20, sl_pct: float = 0.04,
                 tp_pct: float = 0.08, be_trigger_pct: float = 0.04) -> None:
        super().__init__(asset, initial_capital)
        self.window = window
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct
        self.be_trigger_pct = be_trigger_pct

    def run(self) -> None:
        """Exécute la boucle de backtest Trend Following (conforme au script original)."""
        # 1. Préparation des données — Donchian sur Close (comme le script original)
        df = self.asset.prices.values.to_frame(name='Close')
        df['Max_Indicator'] = calc_donchian_channel(df['Close'], window=self.window).shift(1)
        df = df.dropna()

        # 2. Initialisation
        cash = self.initial_capital
        position = 0.0
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        break_even_active = False

        equity_curve_values = []
        positions_history = []

        # 3. Boucle de backtest
        for i in range(len(df)):
            price = df['Close'].iloc[i]
            high_20 = df['Max_Indicator'].iloc[i]

            # Logique de sortie (si en position)
            if position > 0:
                if price <= stop_loss:
                    cash = position * price
                    position = 0.0
                elif price >= take_profit:
                    cash = position * price
                    position = 0.0
                elif not break_even_active and price >= entry_price * (1 + self.be_trigger_pct):
                    stop_loss = entry_price * 1.005
                    break_even_active = True

            # Logique d'entrée — breakout du Close au-dessus du Donchian Close
            if position == 0 and price > high_20:
                position = cash / price
                entry_price = price
                cash = 0.0
                stop_loss = entry_price * (1 - self.sl_pct)
                take_profit = entry_price * (1 + self.tp_pct)
                break_even_active = False

            current_equity = cash if position == 0 else position * price
            equity_curve_values.append(current_equity)
            positions_history.append(position)

        # 4. Sauvegarde
        self.signals = df
        self.equity_curve = equity_curve_values
        self.positions = positions_history
        self.cash_history = [cash] * len(df)


class SniperStrategy(BaseStrategy):
    """
    Moteur de stratégie Sniper (Fat Tail Hunter après compression).
    Identique au script original : breakout Bollinger momentum, long only,
    SL -15% / TP +50%, seuil bandwidth dynamique (20e percentile).
    """
    def __init__(self, asset: Asset, initial_capital: float = 20000.0,
                 sl_pct: float = 0.15, tp_pct: float = 0.50) -> None:
        super().__init__(asset, initial_capital)
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct

    def run(self) -> None:
        """Exécute la boucle de backtest Sniper (conforme au script original)."""
        # 1. Préparation des données
        df = self.asset.prices.values.to_frame(name='Close')

        # 2. Calcul des indicateurs Bollinger
        bb = calc_bollinger_bands(df['Close'], window=20)
        df['Upper'] = bb['Upper']
        df['Bandwidth'] = bb['Bandwidth']
        df = df.dropna()

        # 3. Seuil de compression dynamique : 20e percentile (comme le script original)
        bandwidth_threshold = df['Bandwidth'].quantile(0.20)

        # 4. Initialisation
        cash = self.initial_capital
        position = 0.0
        entry_price = 0.0
        stop_loss = 0.0

        equity_curve_values = []
        positions_history = []

        # 5. Boucle de backtest
        for i in range(len(df)):
            price = df['Close'].iloc[i]
            upper_band = df['Upper'].iloc[i]
            prev_bandwidth = df['Bandwidth'].iloc[i - 1] if i > 0 else 1.0

            # Logique de sortie
            if position > 0:
                if price <= stop_loss:
                    cash = position * price
                    position = 0.0
                elif price >= entry_price * (1 + self.tp_pct):
                    cash = position * price
                    position = 0.0

            # Logique d'entrée — cassure bande haute après compression (momentum long)
            if position == 0 and price > upper_band and prev_bandwidth < bandwidth_threshold:
                position = cash / price
                entry_price = price
                cash = 0.0
                stop_loss = entry_price * (1 - self.sl_pct)

            current_equity = cash if position == 0 else position * price
            equity_curve_values.append(current_equity)
            positions_history.append(position)

        # 6. Sauvegarde
        self.signals = df
        self.equity_curve = equity_curve_values
        self.positions = positions_history
        self.cash_history = [cash] * len(df)
