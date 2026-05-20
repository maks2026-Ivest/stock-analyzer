import pandas as pd

# --- США: S&P 500 + NASDAQ 100 ---
sp500_url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv'
nasdaq100_url = 'https://raw.githubusercontent.com/Ate329/top-us-stock-tickers/main/tickers/top_100.csv'

sp500 = pd.read_csv(sp500_url)
us1 = sp500['Symbol'].str.replace('.', '-').tolist()

nasdaq100 = pd.read_csv(nasdaq100_url)
us2 = nasdaq100['Symbol'].str.replace('.', '-').tolist()

us_tickers = sorted(set(us1 + us2))
pd.DataFrame({'ticker': us_tickers}).to_csv('us_tickers.csv', index=False)
print(f"🇺🇸 США: {len(us_tickers)} тикеров")

# --- Европа: STOXX 600 ---
stoxx_url = 'https://raw.githubusercontent.com/amontalenti/stoxx/main/data/stoxx_600_tickers.csv'
stoxx = pd.read_csv(stoxx_url)
if 'Symbol' in stoxx.columns:
    eu_tickers = stoxx['Symbol'].tolist()
else:
    eu_tickers = stoxx.iloc[:, 0].tolist()
pd.DataFrame({'ticker': eu_tickers}).to_csv('stoxx600_full.csv', index=False)
print(f"🇪🇺 Европа: {len(eu_tickers)} тикеров")
