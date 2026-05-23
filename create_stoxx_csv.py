import pandas as pd

url = 'https://raw.githubusercontent.com/yfiua/index-constituents/main/constituents-stoxx600.csv'
df = pd.read_csv(url)
# В этом CSV колонка с тикерами называется 'Symbol'
tickers = df['Symbol'].tolist()
# Сохраняем в нужном формате
pd.DataFrame({'ticker': tickers}).to_csv('stoxx600_full.csv', index=False)
print(f"✅ Загружено {len(tickers)} тикеров STOXX 600")
print("Примеры:", tickers[:5])
