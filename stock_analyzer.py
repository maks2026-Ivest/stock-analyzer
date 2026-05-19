#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
import time
import warnings
warnings.filterwarnings('ignore')

# --- НАДЁЖНЫЕ ФУНКЦИИ ЗАГРУЗКИ СПИСКОВ (без Wikipedia, с прямыми CSV) ---

def get_sp500_tickers():
    """Загружает список S&P 500 из надёжного CSV-репозитория"""
    url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv'
    try:
        df = pd.read_csv(url)
        tickers = df['Symbol'].str.replace('.', '-').tolist()
        return tickers
    except Exception as e:
        print(f"Ошибка загрузки S&P 500: {e}")
        return []

def get_nasdaq100_tickers():
    """Загружает список NASDAQ 100 из надёжного CSV-репозитория"""
    url = 'https://raw.githubusercontent.com/Ate329/top-us-stock-tickers/main/tickers/top_100.csv'
    try:
        df = pd.read_csv(url)
        tickers = df['Symbol'].str.replace('.', '-').tolist()
        return tickers
    except Exception as e:
        print(f"Ошибка загрузки NASDAQ 100: {e}")
        return []

def get_stoxx600_tickers():
    """Загружает список STOXX 600 с investing.com через парсинг HTML"""
    url = 'https://www.investing.com/indices/stoxx-600-components'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'common-table'})
        if not table:
            print("  Не удалось найти таблицу на странице investing.com")
            return []
        tickers = []
        rows = table.find_all('tr')
        for row in rows[1:]:   # пропускаем заголовок
            cells = row.find_all('td')
            if len(cells) > 1:
                ticker = cells[1].get_text(strip=True)
                if ticker:
                    tickers.append(ticker)
        return tickers
    except Exception as e:
        print(f"Ошибка при парсинге STOXX 600: {e}")
        # Резервный список крупнейших европейских компаний
        return ['ASML.AS', 'SAP.DE', 'IFX.DE', 'OR.PA', 'TTE.PA', 'SAN.PA', 'NOVO-B.CO', 'MC.PA', 'NESN.SW', 'ULVR.L']

# --- Функция получения метрик (с защитой от ошибок) ---
def get_stock_metrics(ticker, region):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        pe = info.get('trailingPE')
        peg = info.get('pegRatio')
        roe = info.get('returnOnEquity')
        revenue_growth = None
        
        # Рост выручки (необязательно, если не получится — пропускаем)
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
        
        # Расчёт Total Score
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
        
        # Если нет ни PEG, ни P/E, ни ROE — не включаем в результат
        if total_score == 0:
            return None
        
        return {
            'ticker': ticker,
            'region': region,
            'pe': pe,
            'peg': peg,
            'roe': roe,
            'revenue_growth': revenue_growth,
            'total': total_score
        }
    except Exception:
        # Не выводим ошибку для каждого тикера, чтобы не засорять лог
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
    
    # Загружаем списки
    print("Загружаю список S&P 500...")
    sp500 = get_sp500_tickers()
    print(f"S&P 500: {len(sp500)} тикеров")
    
    print("Загружаю список NASDAQ 100...")
    nasdaq100 = get_nasdaq100_tickers()
    print(f"NASDAQ 100: {len(nasdaq100)} тикеров")
    
    print("Загружаю список STOXX 600...")
    stoxx600 = get_stoxx600_tickers()
    print(f"STOXX 600: {len(stoxx600)} тикеров")
    
    # Объединяем тикеры США (S&P 500 + NASDAQ 100, убираем дубликаты)
    us_tickers = list(set(sp500 + nasdaq100))
    eu_tickers = stoxx600
    
    print(f"\n🇺🇸 Всего уникальных тикеров США: {len(us_tickers)}")
    print(f"🇪🇺 Всего тикеров Европы: {len(eu_tickers)}")
    
    all_results = []
    
    # --- Анализ США с задержкой ---
    print("\n🇺🇸 Анализ компаний США...")
    for i, ticker in enumerate(us_tickers):
        if i % 50 == 0:
            print(f"  Обработано {i} из {len(us_tickers)}...")
        m = get_stock_metrics(ticker, 'US')
        if m:
            all_results.append(m)
        time.sleep(0.3)  # задержка 300 мс между запросами
    
    # --- Анализ Европы с задержкой ---
    print("\n🇪🇺 Анализ компаний Европы...")
    for i, ticker in enumerate(eu_tickers):
        if i % 50 == 0:
            print(f"  Обработано {i} из {len(eu_tickers)}...")
        m = get_stock_metrics(ticker, 'EU')
        if m:
            all_results.append(m)
        time.sleep(0.3)
    
    # Сортировка
    all_results.sort(key=lambda x: x['total'], reverse=True)
    
    # Формирование отчёта
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append(f"📈 ОТЧЁТ ПО АКЦИЯМ | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 60)
    
    if not all_results:
        report_lines.append("\n⚠️ Не найдено компаний, соответствующих критериям.")
        report_lines.append("Попробуйте ослабить фильтры (PEG, P/E, ROE).")
    else:
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
        
        # Дополнительная статистика
        avg_peg = np.mean([r['peg'] for r in all_results if r.get('peg')])
        report_lines.append(f"📊 Всего проанализировано: {len(all_results)} компаний")
        report_lines.append(f"Средний PEG среди найденных: {avg_peg:.2f}")
    
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
    
    # Сохраняем отчёт в файл (для артефактов GitHub)
    with open(f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w", encoding="utf-8") as f:
        f.write(report)
