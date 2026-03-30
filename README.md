# Run cette consigne dans le REPL/TERMINAL pour lancer le code et le test
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


