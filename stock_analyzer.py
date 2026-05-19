#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import requests
import warnings
warnings.filterwarnings('ignore')

# --- НОВЫЕ ФУНКЦИИ ДЛЯ ЗАГРУЗКИ СПИСКОВ ---
def get_sp500_tickers():
    """Загружает список тикеров S&P 500 с Википедии."""
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    try:
        # Используем pandas для чтения таблицы с википедии
        tables = pd.read_html(url)
        sp500_table = tables[0]
        # Заменяем точки на дефисы в тикерах (требование Yahoo Finance)
        tickers = sp500_table['Symbol'].str.replace('.', '-').tolist()
        return tickers
    except Exception as e:
        print(f"Ошибка при загрузке S&P 500: {e}")
        return []

def get_nasdaq100_tickers():
    """
    Загружает список тикеров NASDAQ-100 из официального CSV-файла Nasdaq.
    Источник: https://www.nasdaq.com/market-activity/quotes/nasdaq-100-index
    """
    url = 'https://www.nasdaq.com/screening/companies-by-name.aspx?exchange=NASDAQ&render=download'
    try:
        df = pd.read_csv(url)
        # Фильтруем компании, относящиеся к NASDAQ 100 (требуется дополнительная логика)
        # В данном случае мы используем упрощённый подход, возвращая все тикеры NASDAQ.
        # Для точного соответствия индексу NASDAQ 100 рекомендуется использовать
        # библиотеку pytickersymbols (см. следующий раздел).
        tickers = df['Symbol'].tolist()
        return tickers[:100]  # Ограничим первыми 100 для примера
    except Exception as e:
        print(f"Ошибка при загрузке NASDAQ-100: {e}")
        return []

def get_stoxx600_tickers():
    """
    Загружает список тикеров STOXX Europe 600, используя библиотеку pytickersymbols.
    Установите её через: pip install pytickersymbols
    """
    try:
        from pytickersymbols import PyTickerSymbols
        stock_data = PyTickerSymbols()
        # Получаем данные по индексу
        stoxx_data = stock_data.get_stoxx_europe_600_yahoo_tickers()
        # Извлекаем только тикеры
        tickers = [item['symbol'] for item in stoxx_data if 'symbol' in item]
        return tickers
    except ImportError:
        print("Библиотека pytickersymbols не установлена.")
        print("Установите её с помощью команды: pip install pytickersymbols")
        return []
    except Exception as e:
        print(f"Ошибка при загрузке STOXX 600: {e}")
        return []
        
# --- Функция получения метрик ---
def get_stock_metrics(ticker, region):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        pe = info.get('trailingPE')
        peg = info.get('pegRatio')
        roe = info.get('returnOnEquity')
        revenue_growth = None
        
        # Пытаемся получить рост выручки
        try:
            financials = stock.financials
            if 'Total Revenue' in financials.index:
                revenue = financials.loc['Total Revenue']
                if len(revenue) >= 3:
                    first = revenue.iloc[-1]
                    last = revenue.iloc[0]
                    years = len(revenue) - 1
                    revenue_growth = (last / first) ** (1/years) - 1
        except:
            pass
        
        # Рассчитываем Total Score
        total_score = 0
        if peg and peg < 1.0:
            total_score += 3
        elif peg and peg < 1.3:
            total_score += 1
        
        if pe:
            if region == 'US' and pe < 15:
                total_score += 2
            elif region == 'EU' and pe < 12:
                total_score += 2
            elif pe < 20:
                total_score += 1
        
        if roe:
            if region == 'US' and roe > 0.15:
                total_score += 2
            elif region == 'EU' and roe > 0.12:
                total_score += 2
            elif roe > 0.10:
                total_score += 1
        
        if revenue_growth and revenue_growth > 0.10:
            total_score += 2
        elif revenue_growth and revenue_growth > 0.05:
            total_score += 1
        
        return {
            'ticker': ticker,
            'region': region,
            'pe': pe,
            'peg': peg,
            'roe': roe,
            'revenue_growth': revenue_growth,
            'total': total_score
        }
    except Exception as e:
        print(f"Ошибка {ticker}: {e}")
        return None

# --- Функция отправки в Telegram ---
def send_to_telegram(message):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("⚠️ Telegram токен или chat_id не найдены")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    if len(message) > 4096:
        message = message[:4093] + "..."
    
    try:
        response = requests.post(url, json={'chat_id': chat_id, 'text': message}, timeout=10)
        if response.status_code == 200:
            print("✅ Отчёт отправлен в Telegram")
        else:
            print(f"❌ Ошибка отправки: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка соединения: {e}")

# --- Основная функция анализа ---
def run_analysis():
    print(f"📊 Анализ запущен {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    all_results = []
    
    # --- ЗАГРУЗКА СПИСКОВ АКЦИЙ ---
    print("Загружаю список S&P 500...")
    us_tickers = get_sp500_tickers()
    print(f"Найдено {len(us_tickers)} акций в S&P 500.")
    
    print("Загружаю список NASDAQ-100...")
    nasdaq_tickers = get_nasdaq100_tickers()
    print(f"Найдено {len(nasdaq_tickers)} акций в NASDAQ-100 (первая сотня).")
    
    print("Загружаю список STOXX 600...")
    eu_tickers = get_stoxx600_tickers()
    print(f"Найдено {len(eu_tickers)} акций в STOXX 600.")

    # --- АНАЛИЗ АКЦИЙ США (из S&P 500 + NASDAQ-100) ---
    print("\n🇺🇸 Анализ компаний США...")
    # Объединяем списки и убираем дубликаты
    all_us_tickers = list(set(us_tickers + nasdaq_tickers))
    print(f"Анализирую {len(all_us_tickers)} уникальных акций США...")
    
    # --- АНАЛИЗ АКЦИЙ ЕВРОПЫ (из STOXX 600) ---
    print("\n🇪🇺 Анализ компаний Европы...")
    print(f"Анализирую {len(eu_tickers)} акций Европы...")
    
    
    # Сортировка по total score
    all_results.sort(key=lambda x: x['total'], reverse=True)
    
    # Формирование отчёта
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append(f"📈 ОТЧЁТ ПО АКЦИЯМ | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 60)
    
    report_lines.append("\n🏆 ТОП КАНДИДАТОВ ДЛЯ ДАЛЬНЕЙШЕГО ИЗУЧЕНИЯ:\n")
    
    for i, r in enumerate(all_results[:10], 1):
        report_lines.append(f"{i}. {r['ticker']} ({r['region']}) | Total: {r['total']:.1f}")
        if r.get('peg'):
            if r.get('pe') and r.get('roe'):
                report_lines.append(f"   PEG: {r['peg']:.2f} | P/E: {r['pe']:.1f} | ROE: {r['roe']*100:.1f}%")
            else:
                report_lines.append(f"   PEG: {r['peg']:.2f}")
        if r.get('revenue_growth'):
            report_lines.append(f"   Рост выручки: {r['revenue_growth']*100:.1f}% годовых")
        report_lines.append("")
    
    if all_results and all_results[0].get('peg') and all_results[0]['peg'] < 0.7:
        report_lines.append("🔔 СИГНАЛ: Найдены компании с PEG < 0.7 – потенциальная недооценка!")
    
    report_lines.append("\n" + "=" * 60)
    report_lines.append("⚠️ Дисклеймер: Не индивидуальная инвестиционная рекомендация.")
    report_lines.append("   Изучите бизнес самостоятельно перед принятием решения.")
    report_lines.append("=" * 60)
    
    return "\n".join(report_lines)

# --- ЗАПУСК ---
if __name__ == "__main__":
    report = run_analysis()
    print(report)
    send_to_telegram(report)
    
    with open(f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w", encoding="utf-8") as f:
        f.write(report)
