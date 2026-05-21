import pandas as pd

# Таблица соответствия биржи → суффикс Yahoo Finance
suffix_map = {
    "Euronext Amsterdam": ".AS",
    "Xetra": ".DE",
    "Euronext Paris": ".PA",
    "SIX Swiss": ".SW",
    "Nasdaq Copenhagen": ".CO",
    "LSE": ".L",
    "Bolsa de Madrid": ".MC",
    "SIX Swiss": ".SW",  # для UBS, ABB, Roche, Nestle, Novartis
    "Euronext Brussels": ".BR",
    "Nasdaq Stockholm": ".ST",
    "Borsa Italiana": ".MI",
    "Nasdaq Helsinki": ".HE",
    "Wiener Börse": ".VI",
    "Warsaw Stock Exchange": ".WA",
    "Oslo Stock Exchange": ".OL",
    "Euronext Lisbon": ".LS"
}

# Ваши данные (вы добавили отличный набор!)
data = {
    "Company": ["ASML Holding", "SAP", "Siemens", "Schneider Electric", "Airbus", "ABB", "Novo Nordisk", "Nestle", "Roche", "Novartis", "AstraZeneca", "Sanofi", "LVMH", "Hermes", "L'Oreal", "Unilever", "Inditex", "Adidas", "HSBC", "Allianz", "UBS Group", "BNP Paribas", "Deutsche Boerse", "Shell", "TotalEnergies", "Linde", "Rio Tinto", "Iberdrola"],
    "Exchange": ["Euronext Amsterdam", "Xetra", "Xetra", "Euronext Paris", "Euronext Paris", "SIX Swiss", "Nasdaq Copenhagen", "SIX Swiss", "SIX Swiss", "SIX Swiss", "LSE", "Euronext Paris", "Euronext Paris", "Euronext Paris", "Euronext Paris", "LSE", "Bolsa de Madrid", "Xetra", "LSE", "Xetra", "SIX Swiss", "Euronext Paris", "Xetra", "LSE", "Euronext Paris", "Xetra", "LSE", "Bolsa de Madrid"]
}

df = pd.DataFrame(data)

# Функция для генерации тикера на основе названия и биржи
def generate_ticker(row):
    company = row["Company"]
    exchange = row["Exchange"]
    suffix = suffix_map.get(exchange, "")
    
    # Особые случаи (если нужно вручную поправить)
    overrides = {
        "Novo Nordisk": "NOVO-B.CO",
        "Unilever": "ULVR.L",
        "HSBC": "HSBA.L",
        "Shell": "SHEL.L",
        "Linde": "LIN.DE",
        "Rio Tinto": "RIO.L",
        "Iberdrola": "IBE.MC",
        "Siemens": "SIE.DE",
        "Schneider Electric": "SU.PA",
        "Airbus": "AIR.PA",
        "ABB": "ABBN.SW",
        "Nestle": "NESN.SW",
        "Roche": "ROG.SW",
        "Novartis": "NOVN.SW",
        "AstraZeneca": "AZN.L",
        "Sanofi": "SAN.PA",
        "LVMH": "MC.PA",
        "Hermes": "RMS.PA",
        "L'Oreal": "OR.PA",
        "Adidas": "ADS.DE",
        "Allianz": "ALV.DE",
        "UBS Group": "UBSG.SW",
        "BNP Paribas": "BNP.PA",
        "Deutsche Boerse": "DB1.DE",
        "TotalEnergies": "TTE.PA",
    }
    
    if company in overrides:
        return overrides[company]
    
    # Стандартное преобразование: убираем пробелы, заменяем на точку, добавляем суффикс
    base = company.split()[0].upper()  # берём первое слово
    if suffix:
        return f"{base}{suffix}"
    else:
        return base  # если суффикс не найден, оставляем как есть

df["ticker"] = df.apply(generate_ticker, axis=1)

# Сохраняем только нужную колонку
df[["ticker"]].to_csv("stoxx600_full.csv", index=False)

print(f"✅ Файл stoxx600_full.csv создан. {len(df)} тикеров.")
print("Первые 5 тикеров:")
print(df["ticker"].head())
