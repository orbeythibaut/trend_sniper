from .asset import Asset, PriceSeries
from .dataloader import DataLoader
from .visualization import PortfolioReport


def run_full_report(
    equity_trend,
    equity_sniper,
    sp500,
    assets_ohlcv=None,
    show_plots: bool = True,
) -> PortfolioReport:
    """
    Utilitaire simple : imprime les tables (ATR + métriques) puis affiche les graphiques.
    Conçu pour être appelé depuis un REPL / notebook sans répéter la plomberie.
    """
    report = PortfolioReport(
        equity_trend=equity_trend,
        equity_sniper=equity_sniper,
        sp500=sp500,
        assets_ohlcv=assets_ohlcv,
    )
    report.print_atr_table()
    report.print_metrics_table()
    if show_plots:
        report.plot(print_tables=False)
    return report


__all__ = ["Asset", "PriceSeries", "DataLoader", "PortfolioReport", "run_full_report"]
