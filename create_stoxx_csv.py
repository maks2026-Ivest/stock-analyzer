# create_stoxx_csv.py
import pandas as pd

# --- 1. Загрузка актуального списка STOXX 600 ---
# Используем ссылку из репозитория yfiua/index-constituents
stoxx_url = 'https://raw.githubusercontent.com/yfiua/index-constituents/main/constituents-stoxx600.csv'

try:
    # Загружаем данные
    stoxx_df = pd.read_csv(stoxx_url)
    
    # Проверяем, есть ли колонка 'Symbol' (так она называется в этом файле)
    if 'Symbol' in stoxx_df.columns:
        tickers = stoxx_df['Symbol'].tolist()
        print(f"✅ STOXX 600: Успешно загружено {len(tickers)} тикеров.")
    else:
        # Если колонка называется иначе, берём первый столбец
        tickers = stoxx_df.iloc[:, 0].tolist()
        print(f"✅ STOXX 600: Успешно загружено {len(tickers)} тикеров (колонка определена автоматически).")

    # Создаём DataFrame только с нужной нам колонкой 'ticker'
    df_to_save = pd.DataFrame({'ticker': tickers})
    df_to_save.to_csv('stoxx600_full.csv', index=False)
    print("💾 Файл 'stoxx600_full.csv' успешно создан и готов к использованию!")

except Exception as e:
    print(f"❌ Ошибка при загрузке или сохранении списка STOXX 600: {e}")
    print("⚠️ Будет использован резервный список.")
    # Резервный список на случай, если основной источник недоступен
    backup_list = ['SAP.DE', 'ASML.AS', 'NOVO-B.CO', 'OR.PA', 'TTE.PA', 'SAN.PA', 'NESN.SW', 'ULVR.L']
    pd.DataFrame({'ticker': backup_list}).to_csv('stoxx600_full.csv', index=False)
    print("💾 Создан файл с резервным списком из 8 тикеров.")
