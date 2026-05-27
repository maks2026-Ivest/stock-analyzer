import yfinance as yf
import pandas as pd

etf = yf.Ticker('QQQ')
holdings = etf.holdings
if holdings is not None and 'Symbol' in holdings.columns:
    tickers = holdings['Symbol'].tolist()
    pd.DataFrame({'ticker': tickers}).to_csv('nasdaq100.csv', index=False)
    print(f'Updated {len(tickers)} tickers')
else:
    print('Failed to get holdings, fallback to static list')
    fallback = ['AAPL','MSFT','NVDA','GOOGL','META','TSLA','AMZN','ADBE','NFLX','PYPL']
    pd.DataFrame({'ticker': fallback}).to_csv('nasdaq100.csv', index=False)
