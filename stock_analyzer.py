#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import requests
import time
import warnings
from bs4 import BeautifulSoup

warnings.filterwarnings('ignore')

# -------------------------------------------------------------------
# 1. ЗАГРУЗКА СПИСКОВ США (ПРЯМО ИЗ ИНТЕРНЕТА)
# -------------------------------------------------------------------
def get_us_tickers():
    """Объединяет S&P 500 и NASDAQ 100, возвращает уникальные тикеры"""
    sp500_url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv'
    nasdaq100_url = 'https://raw.githubusercontent.com/Ate329/top-us-stock-tickers/main/tickers/top_100.csv'
    tickers = []
    try:
        sp500 = pd.read_csv(sp500_url)
        tickers += sp500['Symbol'].str.replace('.', '-').tolist()
    except Exception as e:
        print(f"Ошибка загрузки S&P 500: {e}")
    try:
        nasdaq = pd.read_csv(nasdaq100_url)
        tickers += nasdaq['Symbol'].str.replace('.', '-').tolist()
    except Exception as e:
        print(f"Ошибка загрузки NASDAQ 100: {e}")
    if not tickers:
        # Резервный список, если оба источника недоступны
        print("Использую резервный список США")
        return ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'ADBE', 'PYPL', 'INTC', 'AMD', 'IBM']
    return list(set(tickers))

# -------------------------------------------------------------------
# 2. ЗАГРУЗКА СПИСКА ЕВРОПЫ (ПАРСИНГ + ЛОКАЛЬНЫЙ CSV + РЕЗЕРВ)
# -------------------------------------------------------------------
def get_stoxx600_from_investing():
    """Парсит страницу investing.com и возвращает список тикеров"""
    url = 'https://www.investing.com/indices/stoxx-600-components'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'common-table'})
        if not table:
            return None
        tickers = []
        for row in table.find_all('tr')[1:]:
            cells = row.find_all('td')
            if len(cells) > 1:
                ticker = cells[1].get_text(strip=True)
                if ticker:
                    tickers.append(ticker)
        if len(tickers) > 100:
            return tickers
    except Exception as e:
        print(f"Парсинг investing.com не удался: {e}")
    return None

def load_local_eu_tickers():
    """Пытается загрузить stoxx600_full.csv из репозитория"""
    try:
        df = pd.read_csv('stoxx600_full.csv')
        if 'ticker' in df.columns:
            return df['ticker'].tolist()
        else:
            return df.iloc[:, 0].tolist()
    except:
        return None

def get_eu_tickers():
    """Загружает европейские тикеры: парсинг > локальный CSV > резерв"""
    print("Загружаю европейские тикеры...")
    tickers = get_stoxx600_from_investing()
    if tickers:
        print(f"  Загружено {len(tickers)} тикеров с investing.com")
        return tickers
    tickers = load_local_eu_tickers()
    if tickers:
        print(f"  Загружено {len(tickers)} тикеров из локального CSV")
        return tickers
    # Резервный список крупнейших европейских компаний
    fallback = ['ASML.AS', 'SAP.DE', 'IFX.DE', 'OR.PA', 'TTE.PA', 'SAN.PA', 
                'NOVO-B.CO', 'MC.PA', 'NESN.SW', 'ULVR.L', 'BN.PA', 'AIR.PA',
                'SU.PA', 'ELI.PA', 'INGA.AS', 'UBSG.SW', 'ABBN.SW', 'ROG.SW',
                'RWE.DE', 'LIN.DE']
    print(f"  Использую резервный список ({len(fallback)} тикеров)")
    return fallback

# -------------------------------------------------------------------
# 3. ПОЛУЧЕНИЕ МЕТРИК (VALUE SCORE 0..20)
# -------------------------------------------------------------------
def get_metrics(ticker, region):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        pe = info.get('trailingPE')
        peg = info.get('pegRatio')
        roe = info.get('returnOnEquity')
        fcf_yield = info.get('freeCashflowYield')
        debt = info.get('debtToEquity')
        
        # Рост выручки (3 года CAGR)
        revenue_growth = None
        try:
            fin = stock.financials
            if 'Total Revenue' in fin.index:
                rev = fin.loc['Total Revenue']
                if len(rev) >= 3:
                    first = rev.iloc[-1]
                    last = rev.iloc[0]
                    years = len(rev) - 1
                    revenue_growth = (last / first) ** (1/years) - 1
        except:
            pass
        
        score = 0.0
        # PEG
        if peg is not None:
            if peg < 0.7:
                score += 5.0
            elif peg < 1.0:
                score += 4.0
            elif peg < 1.3:
                score += 2.0
            elif peg < 1.6:
                score += 1.0
        # P/E
        if pe is not None:
            target = 15 if region == 'US' else 12
            if pe < target:
                score += max(0, 4.0 * (1 - pe / target))
            elif pe < target * 1.3:
                score += 1.0
            elif pe < target * 1.6:
                score += 0.5
        # ROE
        if roe is not None:
            if region == 'US':
                if roe > 0.25:
                    score += 4.0
                elif roe > 0.20:
                    score += 3.0
                elif roe > 0.15:
                    score += 2.0
                elif roe > 0.10:
                    score += 1.0
            else:
                if roe > 0.20:
                    score += 4.0
                elif roe > 0.15:
                    score += 3.0
                elif roe > 0.12:
                    score += 2.0
                elif roe > 0.08:
                    score += 1.0
        # Рост выручки
        if revenue_growth is not None:
            if revenue_growth > 0.20:
                score += 4.0
            elif revenue_growth > 0.15:
                score += 3.0
            elif revenue_growth > 0.10:
                score += 2.0
            elif revenue_growth > 0.05:
                score += 1.0
        # FCF Yield
        if fcf_yield is not None:
            if fcf_yield > 0.08:
                score += 2.0
            elif fcf_yield > 0.05:
                score += 1.0
        # Штраф за долг
        if debt is not None:
            if debt > 1.5:
                score -= 2.0
            elif debt > 1.0:
                score -= 1.0
            elif debt > 0.7:
                score -= 0.5
        if score == 0:
            return None
        return {
            'ticker': ticker,
            'region': region,
            'pe': pe,
            'peg': peg,
            'roe': roe,
            'revenue_growth': revenue_growth,
            'fcf_yield': fcf_yield,
            'debt': debt,
            'total': round(score, 2)
        }
    except Exception:
        return None

# -------------------------------------------------------------------
# 4. ОТПРАВКА В TELEGRAM
# -------------------------------------------------------------------
def send_telegram(text):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("⚠️ Нет токена или chat_id")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    if len(text) > 4096:
        text = text[:4093] + "..."
    try:
        r = requests.post(url, json={'chat_id': chat_id, 'text': text}, timeout=10)
        if r.status_code == 200:
            print("✅ Отправлено")
        else:
            print(f"Ошибка {r.status_code}")
    except Exception as e:
        print(f"Ошибка: {e}")

# -------------------------------------------------------------------
# 5. ОСНОВНАЯ ФУНКЦИЯ
# -------------------------------------------------------------------
def run():
    print(f"📊 Старт {datetime.now()}\n")
    
    # Загрузка списков
    us = get_us_tickers()
    eu = get_eu_tickers()
    
    print(f"🇺🇸 США: загружено {len(us)} тикеров")
    print(f"🇪🇺 Европа: загружено {len(eu)} тикеров")
    
    all_res = []
    us_processed = 0
    eu_processed = 0
    
    # НОВОЕ: списки для непрошедших компаний
    failed_us = []
    failed_eu = []
    
    # Сканирование США
    print("\n🇺🇸 Сканирование США...")
    for i, t in enumerate(us):
        if i % 50 == 0:
            print(f"  {i}/{len(us)}")
        m = get_metrics(t, 'US')
        if m:
            all_res.append(m)
            us_processed += 1
        else:
            failed_us.append(t)   # НОВОЕ
        time.sleep(0.25)
    
    # Сканирование Европы
    print("\n🇪🇺 Сканирование Европы...")
    for i, t in enumerate(eu):
        if i % 50 == 0:
            print(f"  {i}/{len(eu)}")
        m = get_metrics(t, 'EU')
        if m:
            all_res.append(m)
            eu_processed += 1
        else:
            failed_eu.append(t)   # НОВОЕ
        time.sleep(0.25)
    
    all_res.sort(key=lambda x: x['total'], reverse=True)
    top20 = all_res[:20]
    total_analyzed = len(all_res)
    
    # Средний PEG
    peg_values = [r['peg'] for r in all_res if r.get('peg') is not None]
    avg_peg = np.mean(peg_values) if peg_values else 0
    
    lines = []
    lines.append("="*60)
    lines.append(f"📈 ТОП-20 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("="*60)
    for i, r in enumerate(top20, 1):
        lines.append(f"{i}. {r['ticker']} ({r['region']}) | Score: {r['total']:.2f}")
        detail = []
        if r.get('peg'): detail.append(f"PEG: {r['peg']:.2f}")
        if r.get('pe'): detail.append(f"P/E: {r['pe']:.1f}")
        if r.get('roe'): detail.append(f"ROE: {r['roe']*100:.1f}%")
        if detail:
            lines.append("   " + " | ".join(detail))
        if r.get('revenue_growth'):
            lines.append(f"   Рост выручки: {r['revenue_growth']*100:.1f}%")
        if r.get('fcf_yield'):
            lines.append(f"   FCF Yield: {r['fcf_yield']*100:.1f}%")
        lines.append("")
    
    # Статистика обработки
    lines.append(f"📊 **Статистика обработки:**")
    lines.append(f"   🇺🇸 США: загружено {len(us)}, проанализировано {us_processed}, не прошло {len(failed_us)}")
    lines.append(f"   🇪🇺 Европа: загружено {len(eu)}, проанализировано {eu_processed}, не прошло {len(failed_eu)}")
    lines.append(f"   📋 Всего проанализировано (score > 0): {total_analyzed}")
    if peg_values:
        lines.append(f"   📈 Средний PEG среди найденных: {avg_peg:.2f}")
    
    # НОВОЕ: показываем первые 10 непрошедших тикеров (если они есть)
    if failed_us:
        lines.append(f"\n⚠️ Примеры тикеров США, не прошедших фильтр (первые 10):")
        lines.append(f"   {', '.join(failed_us[:10])}")
    if failed_eu:
        lines.append(f"\n⚠️ Примеры тикеров Европы, не прошедших фильтр (первые 10):")
        lines.append(f"   {', '.join(failed_eu[:10])}")
    
    lines.append("="*60)
    lines.append("⚠️ Не ИИР. Изучите бизнес самостоятельно.")
    
    # Дополнительно: сохраняем полный список непрошедших в CSV (артефакт)
    # Это позволит скачать файл после выполнения workflow
    if failed_us or failed_eu:
        df_failed = pd.DataFrame({
            'ticker': failed_us + failed_eu,
            'region': ['US']*len(failed_us) + ['EU']*len(failed_eu)
        })
        df_failed.to_csv('failed_tickers.csv', index=False)
        print(f"💾 Список непрошедших компаний сохранён в failed_tickers.csv")
    
    report = "\n".join(lines)
    print(report)
    send_telegram(report)
    
    # Сохраняем отчёт в файл для артефакта (если нужно)
    with open(f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\n✅ Готово")

if __name__ == "__main__":
    run()
