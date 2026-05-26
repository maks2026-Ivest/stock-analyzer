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
# 1. ЗАГРУЗКА СПИСКОВ США (РАЗДЕЛЬНО ДЛЯ S&P 500 И NASDAQ 100)
# -------------------------------------------------------------------
def load_sp500_tickers():
    """Загружает список S&P 500"""
    url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv'
    try:
        df = pd.read_csv(url)
        tickers = df['Symbol'].str.replace('.', '-').tolist()
        return tickers
    except Exception as e:
        print(f"Ошибка загрузки S&P 500: {e}")
        return []

def load_nasdaq100_tickers():
    """Загружает список NASDAQ 100: онлайн-источники > локальный CSV > резервный список"""
    
    # 1. Онлайн-источник (yfiua)
    url = 'https://yfiua.github.io/index-constituents/constituents-nasdaq100.csv'
    try:
        df = pd.read_csv(url)
        if 'Symbol' in df.columns:
            tickers = df['Symbol'].tolist()
        else:
            tickers = df.iloc[:, 0].tolist()
        tickers = [t.strip() for t in tickers if isinstance(t, str) and t.strip()]
        print(f"✅ NASDAQ 100: загружено {len(tickers)} тикеров из онлайн-источника (yfiua)")
        return tickers
    except Exception as e:
        print(f"Ошибка загрузки из {url}: {e}")
    
    # 2. Резервный онлайн-источник (johnbumgardner)
    fallback_url = 'https://raw.githubusercontent.com/johnbumgardner/nasdaq100/master/nasdaq100.csv'
    try:
        df = pd.read_csv(fallback_url)
        if 'Symbol' in df.columns:
            tickers = df['Symbol'].tolist()
        elif 'Ticker' in df.columns:
            tickers = df['Ticker'].tolist()
        else:
            tickers = df.iloc[:, 0].tolist()
        tickers = [t.strip() for t in tickers if isinstance(t, str) and t.strip()]
        print(f"✅ NASDAQ 100: загружено {len(tickers)} тикеров из онлайн-источника (johnbumgardner)")
        return tickers
    except Exception as e:
        print(f"Ошибка загрузки из {fallback_url}: {e}")
    
    # 3. Локальный CSV-файл (как для Европы)
    try:
        df = pd.read_csv('nasdaq100.csv')
        if 'ticker' in df.columns:
            tickers = df['ticker'].tolist()
        else:
            tickers = df.iloc[:, 0].tolist()
        tickers = [str(t).strip() for t in tickers if str(t).strip()]
        if tickers:
            print(f"✅ NASDAQ 100: загружено {len(tickers)} тикеров из локального CSV")
            return tickers
    except Exception as e:
        print(f"Локальный файл nasdaq100.csv не загружен: {e}")
    
    # 4. Ручной резервный список
    fallback_list = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AVGO', 'AMD', 'ASML', 'ORCL', 'CRM',
    'AMZN', 'COST', 'WMT', 'HD', 'NKE', 'V', 'MA', 'JPM', 'BAC', 'LLY',
    'UNH', 'JNJ', 'MRK', 'ABBV', 'TSLA', 'XOM', 'CVX', 'CAT', 'GE', 'NFLX']
    print(f"⚠️ Использую резервный список из {len(fallback_list)} тикеров")
    return fallback_list

# -------------------------------------------------------------------
# 2. ЗАГРУЗКА СПИСКА ЕВРОПЫ (ЛОКАЛЬНЫЙ CSV + РЕЗЕРВ)
# -------------------------------------------------------------------
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
    """Загружает европейские тикеры: локальный CSV > резерв"""
    print("Загружаю европейские тикеры...")
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
# 5. ОСНОВНАЯ ФУНКЦИЯ (С РАЗДЕЛЬНОЙ СТАТИСТИКОЙ ПО ИНДЕКСАМ США)
# -------------------------------------------------------------------
def run():
    print(f"📊 Старт {datetime.now()}\n")
    
    # --- Загрузка списков США раздельно ---
    sp500_tickers = load_sp500_tickers()
    nasdaq100_tickers = load_nasdaq100_tickers()
    
    # Объединение для сканирования (уникальные)
    us_tickers = list(set(sp500_tickers + nasdaq100_tickers))
    
    print(f"🇺🇸 S&P 500: загружено {len(sp500_tickers)} тикеров")
    print(f"🇺🇸 NASDAQ 100: загружено {len(nasdaq100_tickers)} тикеров")
    print(f"🇺🇸 Всего уникальных тикеров США: {len(us_tickers)}")
    
    # --- Загрузка европейских тикеров ---
    eu_tickers = get_eu_tickers()
    print(f"🇪🇺 Европа: загружено {len(eu_tickers)} тикеров")
    
    all_res = []
    
    # Счётчики для США по индексам
    sp500_processed = 0
    nasdaq100_processed = 0
    sp500_failed = []
    nasdaq100_failed = []
    
    # Сканирование США (уникальные тикеры)
    print("\n🇺🇸 Сканирование США...")
    for i, t in enumerate(us_tickers):
        if i % 50 == 0:
            print(f"  {i}/{len(us_tickers)}")
        m = get_metrics(t, 'US')
        if m:
            all_res.append(m)
        # Определяем принадлежность к индексам
        in_sp500 = t in sp500_tickers
        in_nasdaq = t in nasdaq100_tickers
        if m:
            if in_sp500:
                sp500_processed += 1
            if in_nasdaq:
                nasdaq100_processed += 1
        else:
            if in_sp500:
                sp500_failed.append(t)
            if in_nasdaq:
                nasdaq100_failed.append(t)
        time.sleep(0.25)
    
    # Сканирование Европы
    eu_processed = 0
    eu_failed = []
    print("\n🇪🇺 Сканирование Европы...")
    for i, t in enumerate(eu_tickers):
        if i % 50 == 0:
            print(f"  {i}/{len(eu_tickers)}")
        m = get_metrics(t, 'EU')
        if m:
            all_res.append(m)
            eu_processed += 1
        else:
            eu_failed.append(t)
        time.sleep(0.25)
    
    # Сортировка и топ-20
    all_res.sort(key=lambda x: x['total'], reverse=True)
    top20 = all_res[:20]
    total_analyzed = len(all_res)
    peg_values = [r['peg'] for r in all_res if r.get('peg') is not None]
    avg_peg = np.mean(peg_values) if peg_values else 0
    
    # Формирование отчёта
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
    lines.append(f"   🇺🇸 S&P 500: загружено {len(sp500_tickers)}, проанализировано {sp500_processed}, не прошло {len(sp500_failed)}")
    lines.append(f"   🇺🇸 NASDAQ 100: загружено {len(nasdaq100_tickers)}, проанализировано {nasdaq100_processed}, не прошло {len(nasdaq100_failed)}")
    lines.append(f"   🇺🇸 Всего уникальных тикеров США: {len(us_tickers)}")
    lines.append(f"   🇪🇺 Европа: загружено {len(eu_tickers)}, проанализировано {eu_processed}, не прошло {len(eu_failed)}")
    lines.append(f"   📋 Всего проанализировано (score > 0): {total_analyzed}")
    if peg_values:
        lines.append(f"   📈 Средний PEG среди найденных: {avg_peg:.2f}")
    
    # Первые 10 непрошедших (для примера)
    if sp500_failed:
        lines.append(f"\n⚠️ Примеры тикеров S&P 500, не прошедших фильтр (первые 10):")
        lines.append(f"   {', '.join(sp500_failed[:10])}")
    if nasdaq100_failed:
        lines.append(f"\n⚠️ Примеры тикеров NASDAQ 100, не прошедших фильтр (первые 10):")
        lines.append(f"   {', '.join(nasdaq100_failed[:10])}")
    if eu_failed:
        lines.append(f"\n⚠️ Примеры тикеров Европы, не прошедших фильтр (первые 10):")
        lines.append(f"   {', '.join(eu_failed[:10])}")
    
    lines.append("="*60)
    lines.append("⚠️ Не ИИР. Изучите бизнес самостоятельно.")
    
    # Сохраняем непрошедшие в CSV (артефакт)
    if sp500_failed or nasdaq100_failed or eu_failed:
        failed_data = []
        for t in sp500_failed:
            failed_data.append({'ticker': t, 'region': 'S&P 500'})
        for t in nasdaq100_failed:
            failed_data.append({'ticker': t, 'region': 'NASDAQ 100'})
        for t in eu_failed:
            failed_data.append({'ticker': t, 'region': 'EU'})
        df_failed = pd.DataFrame(failed_data)
        df_failed.to_csv('failed_tickers.csv', index=False)
        print(f"💾 Список непрошедших компаний сохранён в failed_tickers.csv")
    
    report = "\n".join(lines)
    print(report)
    send_telegram(report)
    
    with open(f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\n✅ Готово")

if __name__ == "__main__":
    run()
