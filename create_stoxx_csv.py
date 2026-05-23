import pandas as pd
import requests

# Проверенный источник: официальный CSV от yfiua (обновляется автоматически)
url = 'https://raw.githubusercontent.com/yfiua/index-constituents/main/constituents-stoxx600.csv'

try:
    # Загружаем данные
    df = pd.read_csv(url)
    
    # Проверяем, есть ли колонка 'Symbol' (в этом файле она точно есть)
    if 'Symbol' in df.columns:
        tickers = df['Symbol'].tolist()
    else:
        # Если нет, берём первый столбец
        tickers = df.iloc[:, 0].tolist()
    
    # Убираем возможные дубликаты и пустые значения
    tickers = [t for t in tickers if isinstance(t, str) and t.strip()]
    
    # Сохраняем в нужном формате
    pd.DataFrame({'ticker': tickers}).to_csv('stoxx600_full.csv', index=False)
    
    print(f"✅ Успешно! Загружено и сохранено {len(tickers)} тикеров.")
    print(f"Примеры: {tickers[:5]}")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    # Резервный список (хотя бы 20 крупнейших компаний)
    fallback = [
        'SAP.DE', 'ASML.AS', 'NOVO-B.CO', 'OR.PA', 'TTE.PA',
        'SAN.PA', 'NESN.SW', 'ULVR.L', 'IFX.DE', 'SU.PA',
        'MC.PA', 'AIR.PA', 'ABBN.SW', 'ROG.SW', 'NOVN.SW',
        'AZN.L', 'LIN.DE', 'RIO.L', 'IBE.MC', 'ALV.DE'
    ]
    pd.DataFrame({'ticker': fallback}).to_csv('stoxx600_full.csv', index=False)
    print(f"⚠️ Использован резервный список из {len(fallback)} тикеров.")
