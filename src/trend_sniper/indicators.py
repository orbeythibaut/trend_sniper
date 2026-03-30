# src/trend_sniper/indicators.py
import pandas as pd

def calc_donchian_channel(series: pd.Series, window: int = 20) -> pd.Series:
    """Calcule la borne supérieure du canal de Donchian (High rolling max)."""
    # Dans le projet original : High.rolling(window=20).max()
    return series.rolling(window=window).max()

def calc_atr(df: "pd.DataFrame", window: int = 14) -> "pd.Series":
    """Calcule l'Average True Range (ATR) de Wilder sur window jours."""
    high, low, close = df['High'], df['Low'], df['Close']
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()

def calc_bollinger_bands(series: pd.Series, window: int = 20) -> pd.DataFrame:
    """
    Calcule la Moyenne Mobile Simple et la Bandwidth (compression).
    window=20, std=2 (standards).
    """
    sma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    
    upper = sma + (2 * std)
    lower = sma - (2 * std)
    
    # Indicateur de compression (Bandwidth) : (Sup - Inf) / SMA
    # Utilisé dans le projet Sniper
    bandwidth = (upper - lower) / sma
    
    return pd.DataFrame({
        'SMA': sma,
        'Upper': upper,
        'Lower': lower,
        'Bandwidth': bandwidth
    })