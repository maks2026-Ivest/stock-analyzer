import pandas as pd

# Источник: надёжный репозиторий с ежедневным обновлением (пример)
url = 'https://raw.githubusercontent.com/amontalenti/stoxx/main/data/stoxx_600_tickers.csv'
try:
    df = pd.read_csv(url)
    tickers = df['Symbol'].tolist() if 'Symbol' in df.columns else df.iloc[:,0].tolist()
    pd.DataFrame({'ticker': tickers}).to_csv('stoxx600_full.csv', index=False)
    print(f"Сохранено {len(tickers)} тикеров")
except Exception as e:
    print("Ошибка:", e)
