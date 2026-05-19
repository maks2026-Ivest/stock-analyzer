import pandas as pd

# --- S&P 500 ---
url_sp500 = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
sp500 = pd.read_html(url_sp500)[0]
us_tickers = sp500['Symbol'].str.replace('.', '-').tolist()

# --- NASDAQ 100 (альтернативный источник) ---
# Используем известный репозиторий на GitHub (обновляется ежедневно)
url_nasdaq = 'https://raw.githubusercontent.com/fiscalnote/stock-list/main/data/nasdaq-100.csv'
nasdaq100 = pd.read_csv(url_nasdaq)
us_tickers += nasdaq100['Symbol'].tolist()
us_tickers = list(set(us_tickers))  # убираем дубликаты

# --- STOXX 600 (упрощённо, через готовый список) ---
# Берём из проверенного источника: https://www.stoxx.com/index-components?symbol=SXXP
# Но для простоты возьмём CSV-файл из открытого репозитория
url_stoxx = 'https://raw.githubusercontent.com/amontalenti/stoxx/main/data/stoxx_600_tickers.csv'
stoxx = pd.read_csv(url_stoxx)
eu_tickers = stoxx['Ticker'].tolist()

# Сохраняем в CSV
pd.DataFrame({'ticker': us_tickers}).to_csv('us_tickers.csv', index=False)
pd.DataFrame({'ticker': eu_tickers}).to_csv('eu_tickers.csv', index=False)

print(f"USA: {len(us_tickers)} tickers")
print(f"Europe: {len(eu_tickers)} tickers")
