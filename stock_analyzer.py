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
    url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv'
    try:
        df = pd.read_csv(url)
        return df['Symbol'].str.replace('.', '-').tolist()
    except Exception as e:
        print(f"Ошибка S&P 500: {e}")
        return []

def load_nasdaq100_tickers():
    """Загружает список NASDAQ 100: онлайн > локальный CSV > резерв"""
    # 1. Онлайн-источник
    url = 'https://yfiua.github.io/index-constituents/constituents-nasdaq100.csv'
    try:
        df = pd.read_csv(url)
        if 'Symbol' in df.columns:
            tickers = df['Symbol'].tolist()
        else:
            tickers = df.iloc[:, 0].tolist()
        tickers = [t.strip() for t in tickers if isinstance(t, str) and t.strip()]
        if tickers:
            print(f"✅ NASDAQ 100: загружено {len(tickers)} тикеров (онлайн)")
            return tickers
    except Exception as e:
        print(f"Ошибка онлайн-источника NASDAQ: {e}")
    
    # 2. Локальный CSV
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
    except:
        pass
    
    # 3. Резерв
    fallback = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'TSLA', 'AMZN', 'ADBE', 'NFLX', 'PYPL']
    print(f"⚠️ Использую резервный список NASDAQ 100 ({len(fallback)})")
    return fallback

def load_local_eu_tickers():
    try:
        df = pd.read_csv('stoxx600_full.csv')
        if 'ticker' in df.columns:
            return df['ticker'].tolist()
        else:
            return df.iloc[:, 0].tolist()
    except:
        return None

def get_eu_tickers():
    print("Загружаю европейские тикеры...")
    tickers = load_local_eu_tickers()
    if tickers:
        print(f"  Загружено {len(tickers)} тикеров из локального CSV")
        return tickers
    fallback = ['ASML.AS', 'SAP.DE', 'IFX.DE', 'OR.PA', 'TTE.PA', 'SAN.PA', 
                'NOVO-B.CO', 'MC.PA', 'NESN.SW', 'ULVR.L', 'BN.PA', 'AIR.PA']
    print(f"  Использую резервный список ({len(fallback)} тикеров)")
    return fallback

# -------------------------------------------------------------------
# 2. ФУНКЦИЯ СБОРА МЕТРИК (ОБЩАЯ ДЛЯ ОБОИХ ПОДХОДОВ)
# -------------------------------------------------------------------
def get_all_metrics(ticker, region):
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
        
        # Рост EPS (3 года CAGR)
        eps_growth = None
        try:
            earn = stock.earnings
            if earn is not None and len(earn) >= 3:
                eps = earn['earnings']
                first = eps.iloc[-1]
                last = eps.iloc[0]
                years = len(eps) - 1
                eps_growth = (last / first) ** (1/years) - 1
        except:
            pass
        
        return {
            'ticker': ticker,
            'region': region,
            'pe': pe,
            'peg': peg,
            'roe': roe,
            'fcf_yield': fcf_yield,
            'debt': debt,
            'revenue_growth': revenue_growth,
            'eps_growth': eps_growth,
        }
    except Exception:
        return None

# -------------------------------------------------------------------
# 3. VALUE SCORE (НЕДООЦЕНЁННОСТЬ)
# -------------------------------------------------------------------
def compute_value_score(m, region):
    if m is None:
        return None
    score = 0.0
    # PEG
    peg = m.get('peg')
    if peg is not None and isinstance(peg, (int, float)):
        if peg < 0.7:
            score += 5.0
        elif peg < 1.0:
            score += 4.0
        elif peg < 1.3:
            score += 2.0
        elif peg < 1.6:
            score += 1.0
    # P/E
    pe = m.get('pe')
    if pe is not None and isinstance(pe, (int, float)):
        target = 15 if region == 'US' else 12
        if pe < target:
            score += max(0, 4.0 * (1 - pe / target))
        elif pe < target * 1.3:
            score += 1.0
        elif pe < target * 1.6:
            score += 0.5
    # ROE
    roe = m.get('roe')
    if roe is not None and isinstance(roe, (int, float)):
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
    rev_g = m.get('revenue_growth')
    if rev_g is not None and isinstance(rev_g, (int, float)):
        if rev_g > 0.20:
            score += 4.0
        elif rev_g > 0.15:
            score += 3.0
        elif rev_g > 0.10:
            score += 2.0
        elif rev_g > 0.05:
            score += 1.0
    # FCF Yield
    fcf = m.get('fcf_yield')
    if fcf is not None and isinstance(fcf, (int, float)):
        if fcf > 0.08:
            score += 2.0
        elif fcf > 0.05:
            score += 1.0
    # Штраф за долг
    debt = m.get('debt')
    if debt is not None and isinstance(debt, (int, float)):
        if debt > 1.5:
            score -= 2.0
        elif debt > 1.0:
            score -= 1.0
        elif debt > 0.7:
            score -= 0.5
    return round(score, 2)
# -------------------------------------------------------------------
# 4. GROWTH SCORE (ПОТЕНЦИАЛ РОСТА)
# -------------------------------------------------------------------
def compute_growth_score(m):
    if m is None:
        return None
    score = 0.0
    rev = m.get('revenue_growth')
    if rev is not None and isinstance(rev, (int, float)):
        if rev > 0.40:
            score += 6.0
        elif rev > 0.30:
            score += 5.0
        elif rev > 0.20:
            score += 4.0
        elif rev > 0.15:
            score += 2.0
        elif rev > 0.10:
            score += 1.0
    eps = m.get('eps_growth')
    if eps is not None and isinstance(eps, (int, float)):
        if eps > 0.40:
            score += 6.0
        elif eps > 0.30:
            score += 5.0
        elif eps > 0.20:
            score += 4.0
        elif eps > 0.15:
            score += 2.0
        elif eps > 0.10:
            score += 1.0
    roe = m.get('roe')
    if roe is not None and isinstance(roe, (int, float)):
        if roe > 0.25:
            score += 4.0
        elif roe > 0.20:
            score += 3.0
        elif roe > 0.15:
            score += 2.0
        elif roe > 0.10:
            score += 1.0
    fcf = m.get('fcf_yield')
    if fcf is not None and isinstance(fcf, (int, float)):
        if fcf > 0.08:
            score += 2.0
        elif fcf > 0.05:
            score += 1.0
    debt = m.get('debt')
    if debt is not None and isinstance(debt, (int, float)):
        if debt > 1.5:
            score -= 2.0
        elif debt > 1.0:
            score -= 1.0
        elif debt > 0.7:
            score -= 0.5
    return round(score, 2)

# -------------------------------------------------------------------
# 5. ОТПРАВКА В TELEGRAM
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
# 6. ОСНОВНАЯ ФУНКЦИЯ (ВЫДАЁТ ДВА ТОПА)
# -------------------------------------------------------------------
def run():
    print(f"📊 Старт {datetime.now()}\n")
    
    # Проверка наличия файлов
    print("Проверка файлов:")
    for f in ['stoxx600_full.csv', 'nasdaq100.csv']:
        if os.path.exists(f):
            print(f"  ✅ {f} найден")
        else:
            print(f"  ❌ {f} НЕ НАЙДЕН")
    
    # Загрузка списков
    sp500 = load_sp500_tickers()
    nasdaq = load_nasdaq100_tickers()
    eu = get_eu_tickers()
    
    us_tickers = list(set(sp500 + nasdaq))
    print(f"🇺🇸 S&P 500: {len(sp500)} | NASDAQ 100: {len(nasdaq)} | Уникальных США: {len(us_tickers)}")
    print(f"🇪🇺 Европа: {len(eu)} тикеров")
    
    all_metrics = []          # (ticker, region, metrics)
    
    # Счётчики для статистики
    sp500_processed = 0
    nasdaq100_processed = 0
    sp500_failed = []
    nasdaq100_failed = []
    
    # Сканирование США
    print("\n🇺🇸 Сканирование США...")
    for i, t in enumerate(us_tickers):
        if i % 50 == 0:
            print(f"  {i}/{len(us_tickers)}")
        m = get_all_metrics(t, 'US')
        # Определяем принадлежность к индексам
        in_sp500 = t in sp500
        in_nasdaq = t in nasdaq
        if m:
            all_metrics.append((t, 'US', m))
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
    for i, t in enumerate(eu):
        if i % 50 == 0:
            print(f"  {i}/{len(eu)}")
        m = get_all_metrics(t, 'EU')
        if m:
            all_metrics.append((t, 'EU', m))
            eu_processed += 1
        else:
            eu_failed.append(t)
        time.sleep(0.25)
    
    # Расчёт оценок
    value_list = []
    growth_list = []
    for ticker, region, m in all_metrics:
        v = compute_value_score(m, region)
        if v is not None and v > 0:
            value_list.append((ticker, region, v, m))
        g = compute_growth_score(m)
        if g is not None and g > 0:
            growth_list.append((ticker, region, g, m))
    
    value_list.sort(key=lambda x: x[2], reverse=True)
    growth_list.sort(key=lambda x: x[2], reverse=True)
    
    top_value = value_list[:15]
    top_growth = growth_list[:15]
    
    total_analyzed = len(all_metrics)
    peg_values = [m['peg'] for _,_,m in all_metrics if m.get('peg') is not None and isinstance(m['peg'], (int,float))]
    avg_peg = np.mean(peg_values) if peg_values else 0
    
    # --- ОТЧЁТ VALUE TOP-15 (со статистикой) ---
    lines1 = []
    lines1.append("="*60)
    lines1.append(f"📈 VALUE TOP-15 (недооценённые) | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines1.append("="*60)
    for i, (ticker, region, score, m) in enumerate(top_value, 1):
        peg = m.get('peg')
        pe = m.get('pe')
        roe = m.get('roe')
        rev = m.get('revenue_growth')
        lines1.append(f"{i}. {ticker} ({region}) | Score: {score:.2f}")
        detail = []
        if peg is not None and isinstance(peg, (int,float)): detail.append(f"PEG: {peg:.2f}")
        if pe is not None and isinstance(pe, (int,float)): detail.append(f"P/E: {pe:.1f}")
        if roe is not None and isinstance(roe, (int,float)): detail.append(f"ROE: {roe*100:.1f}%")
        if detail:
            lines1.append("   " + " | ".join(detail))
        if rev is not None and isinstance(rev, (int,float)):
            lines1.append(f"   Рост выручки: {rev*100:.1f}%")
        lines1.append("")
    
    # Статистика обработки
    lines1.append("📊 **Статистика обработки:**")
    lines1.append(f"   🇺🇸 S&P 500: загружено {len(sp500)}, проанализировано {sp500_processed}, не прошло {len(sp500_failed)}")
    lines1.append(f"   🇺🇸 NASDAQ 100: загружено {len(nasdaq)}, проанализировано {nasdaq100_processed}, не прошло {len(nasdaq100_failed)}")
    lines1.append(f"   🇺🇸 Всего уникальных тикеров США: {len(us_tickers)}")
    lines1.append(f"   🇪🇺 Европа: загружено {len(eu)}, проанализировано {eu_processed}, не прошло {len(eu_failed)}")
    lines1.append(f"   📋 Всего проанализировано (score > 0): {total_analyzed}")
    lines1.append(f"   📈 Средний PEG среди найденных: {avg_peg:.2f}")
    
    # Примеры непрошедших (первые 10)
    if sp500_failed:
        lines1.append(f"\n⚠️ Примеры тикеров S&P 500, не прошедших фильтр (первые 10):")
        lines1.append(f"   {', '.join(sp500_failed[:10])}")
    if nasdaq100_failed:
        lines1.append(f"\n⚠️ Примеры тикеров NASDAQ 100, не прошедших фильтр (первые 10):")
        lines1.append(f"   {', '.join(nasdaq100_failed[:10])}")
    if eu_failed:
        lines1.append(f"\n⚠️ Примеры тикеров Европы, не прошедших фильтр (первые 10):")
        lines1.append(f"   {', '.join(eu_failed[:10])}")
    
    lines1.append("="*60)
    lines1.append("⚠️ Не ИИР. Изучите бизнес самостоятельно.")
    
    # --- ОТЧЁТ GROWTH TOP-15 (без статистики, но можно добавить при желании) ---
    lines2 = []
    lines2.append("="*60)
    lines2.append(f"🚀 GROWTH TOP-15 (высокий потенциал роста) | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines2.append("="*60)
    for i, (ticker, region, score, m) in enumerate(top_growth, 1):
        rev = m.get('revenue_growth')
        eps = m.get('eps_growth')
        roe = m.get('roe')
        pe = m.get('pe')
        lines2.append(f"{i}. {ticker} ({region}) | Score: {score:.2f}")
        detail = []
        if rev is not None and isinstance(rev, (int,float)): detail.append(f"Рост выручки: {rev*100:.1f}%")
        if eps is not None and isinstance(eps, (int,float)): detail.append(f"Рост EPS: {eps*100:.1f}%")
        if roe is not None and isinstance(roe, (int,float)): detail.append(f"ROE: {roe*100:.1f}%")
        if pe is not None and isinstance(pe, (int,float)): detail.append(f"P/E: {pe:.1f}")
        if detail:
            lines2.append("   " + " | ".join(detail))
        lines2.append("")
    lines2.append(f"📊 Всего компаний с Growth Score > 0: {len(growth_list)}")
    lines2.append("="*60)
    lines2.append("⚠️ Не ИИР. Изучите бизнес самостоятельно.")
    
    report1 = "\n".join(lines1)
    report2 = "\n".join(lines2)
    
    print(report1)
    print("\n" + "="*60 + "\n")
    print(report2)
    
    send_telegram(report1)
    time.sleep(1)
    send_telegram(report2)
    
    print("\n✅ Два отчёта отправлены")

if __name__ == "__main__":
    run()
