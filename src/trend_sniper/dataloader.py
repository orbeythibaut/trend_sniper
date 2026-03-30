from pathlib import Path
import pickle
import pandas as pd
import yfinance as yf
from .asset import PriceSeries

class DataLoader:
    """
    Charge les données depuis Yahoo Finance avec le système de cache du cours.
    
    """
    def __init__(self, cache_dir: str = ".cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_path(self, ticker: str, price_col: str, dates: tuple[str, str]) -> Path:
        return self.cache_dir / f"{ticker}_{price_col}_{dates[0]}_{dates[1]}.pkl"

    def _check_date_overlap(self, cached_start, cached_end, req_start, req_end):
        """Détermine le type de chevauchement (Logique Session 2)."""
        if cached_end < req_start or cached_start > req_end:
            return ("miss", None, None)
        if cached_start <= req_start and cached_end >= req_end:
            return ("contains", None, None)
        if cached_start <= req_start and cached_end < req_end:
            return ("overlap_after", cached_end + pd.Timedelta(days=1), req_end)
        if cached_start > req_start and cached_end >= req_end:
            return ("overlap_before", req_start, cached_start - pd.Timedelta(days=1))
        return ("miss", None, None)

    def _load_from_cache(self, ticker, price_col, start_date, end_date):
        """Cherche si des données existent déjà localement."""
        for file_path in self.cache_dir.glob("*.pkl"):
            parts = file_path.stem.split('_')
            if parts[0] == ticker and parts[1] == price_col:
                c_start, c_end = pd.to_datetime(parts[2]), pd.to_datetime(parts[3])
                status, g_start, g_end = self._check_date_overlap(c_start, c_end, start_date, end_date)
                if status != "miss":
                    with open(file_path, 'rb') as f:
                        data = pickle.load(f)
                    df = pd.DataFrame({price_col: data['prices']}, index=pd.to_datetime(data['dates']))
                    return df, status, (g_start, g_end)
        return None, "miss", None

    def _save_to_cache(self, cache_path, prices, dates, ticker, start, end):
        data = {"prices": prices, "dates": dates, "ticker": ticker, "start": start, "end": end}
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)

    def _fetch_from_api(self, ticker, start, end):
        """
        Téléchargement robuste pour éviter l'erreur 'Close'.
        """
        # On télécharge les données
        df = yf.download(ticker, start=start, end=end, progress=False)
        if df.empty:
            raise ValueError(
                f"Aucune donnée trouvée pour {ticker} entre {start} et {end}. "
                "Choisissez une date de début postérieure à l'IPO ou un ticker avec historique disponible."
            )
        # SOLUTION : Si yfinance renvoie un tableau complexe, on le remet à plat
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # On extrait la colonne Close proprement
        series = df['Close']
        
        # Si c'est encore un DataFrame (cas rare), on prend la colonne du ticker
        if isinstance(series, pd.DataFrame):
            series = series[ticker]
            
        return series.ffill().dropna().tz_localize(None)

    def fetch_single_ticker(self, ticker: str, price_col: str, dates: tuple[str, str]) -> PriceSeries:
        """Méthode principale demandée par le prof."""
        req_start, req_end = pd.to_datetime(dates[0]), pd.to_datetime(dates[1])
        cached_df, status, gap = self._load_from_cache(ticker, price_col, req_start, req_end)

        if status == "contains" or status == "exact":
            data = cached_df.loc[req_start:req_end][price_col]
        elif status.startswith("overlap"):
            # On télécharge juste ce qui manque et on fusionne
            new_data = self._fetch_from_api(ticker, gap[0], gap[1])
            combined = pd.concat([cached_df[price_col], new_data]).sort_index()
            combined = combined[~combined.index.duplicated()]
            # On sauve le nouveau cache étendu
            path = self._get_cache_path(ticker, price_col, (combined.index[0].strftime('%Y-%m-%d'), combined.index[-1].strftime('%Y-%m-%d')))
            self._save_to_cache(path, combined.tolist(), combined.index.tolist(), ticker, combined.index[0], combined.index[-1])
            data = combined.loc[req_start:req_end]
        else:
            # Rien en cache : on télécharge tout
            data = self._fetch_from_api(ticker, req_start, req_end)
            path = self._get_cache_path(ticker, price_col, dates)
            self._save_to_cache(path, data.tolist(), data.index.tolist(), ticker, dates[0], dates[1])

        return PriceSeries(data, name=price_col)

    def fetch_data(self, ticker: str, start: str, end: str) -> "pd.DataFrame":
        """Retourne un DataFrame OHLCV complet avec cache (utilisé dans main)."""
        cache_path = self.cache_dir / f"{ticker}_OHLCV_{start}_{end}.pkl"
        if cache_path.exists():
            with open(cache_path, 'rb') as f:
                df = pickle.load(f)
            if df.empty:
                raise ValueError(
                    f"Cache vide pour {ticker} entre {start} et {end}. "
                    "Supprimez le cache ou choisissez une plage de dates valide (après l'IPO)."
                )
            return df
        df = yf.download(ticker, start=start, end=end, progress=False)
        if df.empty:
            raise ValueError(
                f"Aucune donnée trouvée pour {ticker} entre {start} et {end}. "
                "Choisissez une date de début postérieure à l'IPO ou un ticker avec historique disponible."
            )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.ffill().dropna()
        with open(cache_path, 'wb') as f:
            pickle.dump(df, f)
        return df

    def clear_cache(self) -> int:
        count = 0
        for f in self.cache_dir.glob("*.pkl"):
            f.unlink()
            count += 1
        return count
