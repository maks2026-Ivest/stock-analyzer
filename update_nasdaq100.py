import pandas as pd

# Надёжный источник CSV с тикерами NASDAQ 100
url = 'https://raw.githubusercontent.com/johnbumgardner/nasdaq100/master/nasdaq100.csv'

try:
    df = pd.read_csv(url)
    # В этом CSV колонка называется 'Symbol'
    if 'Symbol' in df.columns:
        tickers = df['Symbol'].tolist()
    elif 'Ticker' in df.columns:
        tickers = df['Ticker'].tolist()
    else:
        tickers = df.iloc[:, 0].tolist()
    
    # Очищаем и сохраняем
    tickers = [str(t).strip() for t in tickers if str(t).strip()]
    if tickers:
        pd.DataFrame({'ticker': tickers}).to_csv('nasdaq100.csv', index=False)
        print(f'✅ NASDAQ 100 обновлён: {len(tickers)} тикеров')
    else:
        raise Exception('Empty tickers list')
except Exception as e:
    print(f'Ошибка загрузки: {e}. Использую резервный список.')
    fallback = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'TSLA', 'AMZN', 'ADBE', 'NFLX', 'PYPL']
    pd.DataFrame({'ticker': fallback}).to_csv('nasdaq100.csv', index=False)
