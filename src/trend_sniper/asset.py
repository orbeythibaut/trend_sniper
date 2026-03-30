# src/trend_sniper/asset.py
import pandas as pd

class PriceSeries:
    """
    Encapsule une série temporelle de prix Pandas.
    """
    def __init__(self, values: pd.Series, name: str = "Close") -> None:
        if values.empty:
            raise ValueError("La série de prix ne peut pas être vide.")
        self.values = values
        self.name = name

    def __len__(self) -> int:
        return len(self.values)

class Asset:
    """
    Représente un actif financier (ex: TSLA, PLTR).
    Pattern: Composition (Asset possède une PriceSeries).
    """
    def __init__(self, ticker: str, prices_series: "pd.Series | pd.DataFrame") -> None:
        self.ticker = ticker.upper()
        if isinstance(prices_series, pd.DataFrame):
            self.ohlcv = prices_series
            self.prices = PriceSeries(prices_series["Close"], name="Close")
        else:
            self.ohlcv = None
            self.prices = PriceSeries(prices_series, name="Close")
        
    def __repr__(self) -> str:
        return f"Asset({self.ticker!r}, {len(self.prices)} jours de données)"

    @property
    def current_price(self) -> float:
        """Dernier prix connu."""
        return float(self.prices.values.iloc[-1])