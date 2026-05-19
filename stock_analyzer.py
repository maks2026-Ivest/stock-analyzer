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
# 1. ЗАГРУЗКА СПИСКОВ АКЦИЙ США (S&P 500 + NASDAQ 100)
# -------------------------------------------------------------------

def get_sp500_tickers():
    url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv'
    try:
        df = pd.read_csv(url)
        return df['Symbol'].str.replace('.', '-').tolist()
    except Exception as e:
        print(f"Ошибка S&P 500: {e}")
        return []

def get_nasdaq100_tickers():
    url = 'https://raw.githubusercontent.com/Ate329/top-us-stock-tickers/main/tickers/top_100.csv'
    try:
        df = pd.read_csv(url)
        return df['Symbol'].str.replace('.', '-').tolist()
    except Exception as e:
        print(f"Ошибка NASDAQ 100: {e}")
        return []

# -------------------------------------------------------------------
# 2. ЗАГРУЗКА STOXX 600 (ЕВРОПА) С ПЕРЕКЛЮЧЕНИЕМ ИСТОЧНИКОВ
# -------------------------------------------------------------------

def get_stoxx600_from_github():
    urls = [
        'https://raw.githubusercontent.com/amontalenti/stoxx/main/data/stoxx_600_tickers.csv',
        'https://raw.githubusercontent.com/jamesbcook/STOXX600/main/stoxx600.csv',
    ]
    for url in urls:
        try:
            df = pd.read_csv(url)
            if 'Symbol' in df.columns:
                tickers = df['Symbol'].tolist()
            elif 'Ticker' in df.columns:
                tickers = df['Ticker'].tolist()
            else:
                tickers = df.iloc[:, 0].tolist()
            if len(tickers) > 400:
                return tickers
        except:
            continue
    return None

def get_stoxx600_from_tradingview():
    url = 'https://www.tradingview.com/markets/stocks/indices/stoxx600-components/'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        tickers = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/symbols/' in href:
                ticker = href.split('/symbols/')[-1].split('/')[0].split('?')[0]
                if ticker and ticker not in tickers:
                    tickers.append(ticker)
        if len(tickers) > 100:
            return tickers
    except:
        pass
    return None

def get_stoxx600_from_investing():
    url = 'https://www.investing.com/indices/stoxx-600-components'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
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
    except:
        pass
    return None

def get_stoxx600_tickers():
    print("Загружаю STOXX 600...")
    tickers = get_stoxx600_from_github()
    if tickers:
        print(f"  GitHub: {len(tickers)} тикеров")
        return tickers
    tickers = get_stoxx600_from_tradingview()
    if tickers:
        print(f"  TradingView: {len(tickers)} тикеров")
        return tickers
    tickers = get_stoxx600_from_investing()
    if tickers:
        print(f"  Investing.com: {len(tickers)} тикеров")
        return tickers
    fallback = ['ASML.AS', 'SAP.DE', 'IFX.DE', 'OR.PA', 'TTE.PA', 'SAN.PA', 'NOVO-B.CO', 'MC.PA', 'NESN.SW', 'ULVR.L']
    print(f"  Использую резервный список ({len(fallback)} акций)")
    return fallback

# -------------------------------------------------------------------
# 3. ФУНКЦИЯ ПОЛУЧЕНИЯ МЕТРИК ДЛЯ СКРИНИНГА (быстрая)
# -------------------------------------------------------------------

def get_fast_metrics(ticker, region):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        pe = info.get('trailingPE')
        peg = info.get('pegRatio')
        roe = info.get('returnOnEquity')
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
        total = 0
        if peg and peg < 1.0:
            total += 3
        elif peg and peg < 1.3:
            total += 1
        if pe:
            if region == 'US' and pe < 15:
                total += 2
            elif region == 'EU' and pe < 12:
                total += 2
            elif pe < 20:
                total += 1
        if roe:
            if region == 'US' and roe > 0.15:
                total += 2
            elif region == 'EU' and roe > 0.12:
                total += 2
            elif roe > 0.10:
                total += 1
        if revenue_growth and revenue_growth > 0.10:
            total += 2
        elif revenue_growth and revenue_growth > 0.05:
            total += 1
        if total == 0:
            return None
        return {'ticker': ticker, 'region': region, 'pe': pe, 'peg': peg, 'roe': roe,
                'revenue_growth': revenue_growth, 'total': total}
    except:
        return None

# -------------------------------------------------------------------
# 4. ФУНКЦИЯ ГЛУБОКОГО АНАЛИЗА (для одного тикера)
# -------------------------------------------------------------------

def get_company_info(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    data = {
        'name': info.get('longName', 'N/A'),
        'sector': info.get('sector', 'N/A'),
        'industry': info.get('industry', 'N/A'),
        'country': info.get('country', 'N/A'),
        'website': info.get('website', 'N/A'),
        'summary': info.get('longBusinessSummary', 'Нет описания'),
        'market_cap': info.get('marketCap', 'N/A'),
        'pe': info.get('trailingPE', 'N/A'),
        'forward_pe': info.get('forwardPE', 'N/A'),
        'peg': info.get('pegRatio', 'N/A'),
        'pb': info.get('priceToBook', 'N/A'),
        'roe': info.get('returnOnEquity', 'N/A'),
        'roa': info.get('returnOnAssets', 'N/A'),
        'debt_to_equity': info.get('debtToEquity', 'N/A'),
        'current_ratio': info.get('currentRatio', 'N/A'),
        'dividend_yield': info.get('dividendYield', 'N/A'),
        'fcf_yield': info.get('freeCashflowYield', 'N/A'),
        'beta': info.get('beta', 'N/A'),
        'profit_margin': info.get('profitMargins', 'N/A'),
        'operating_margin': info.get('operatingMargins', 'N/A'),
        'revenue_growth': None,
        'eps_growth': None,
    }
    # Рост выручки
    try:
        fin = stock.financials
        if 'Total Revenue' in fin.index:
            rev = fin.loc['Total Revenue']
            if len(rev) >= 3:
                data['revenue_growth'] = (rev.iloc[0] / rev.iloc[-1]) ** (1/(len(rev)-1)) - 1
    except:
        pass
    # Рост EPS
    try:
        earn = stock.earnings
        if earn is not None and len(earn) >= 3:
            eps = earn['earnings']
            data['eps_growth'] = (eps.iloc[0] / eps.iloc[-1]) ** (1/(len(eps)-1)) - 1
    except:
        pass
    return data, stock

def generate_deep_analysis(ticker, data):
    lines = []
    lines.append(f"🔍 **ГЛУБОКИЙ АНАЛИЗ: {ticker.upper()} – {data['name']}**\n")
    lines.append(f"Сектор: {data['sector']} | Индустрия: {data['industry']} | Страна: {data['country']}")
    if data['summary'] != 'Нет описания':
        summary = data['summary'][:500] + "…" if len(data['summary']) > 500 else data['summary']
        lines.append(f"\n📝 **Описание**: {summary}")
    
    lines.append("\n💰 **Финансы**")
    lines.append(f"Капитализация: {data['market_cap']:,}")
    lines.append(f"P/E (TTM): {data['pe']:.2f}" if isinstance(data['pe'], (int,float)) else f"P/E: {data['pe']}")
    lines.append(f"Forward P/E: {data['forward_pe']:.2f}" if isinstance(data['forward_pe'], (int,float)) else "")
    lines.append(f"PEG: {data['peg']:.2f}" if isinstance(data['peg'], (int,float)) else f"PEG: {data['peg']}")
    lines.append(f"ROE: {data['roe']*100:.1f}%" if isinstance(data['roe'], (int,float)) else f"ROE: {data['roe']}")
    lines.append(f"Долг/Equity: {data['debt_to_equity']:.2f}" if isinstance(data['debt_to_equity'], (int,float)) else "")
    lines.append(f"FCF Yield: {data['fcf_yield']*100:.1f}%" if isinstance(data['fcf_yield'], (int,float)) else "")
    lines.append(f"Дивиденды: {data['dividend_yield']*100:.1f}%" if isinstance(data['dividend_yield'], (int,float)) else "Дивидендов нет")
    
    if data['revenue_growth']:
        lines.append(f"\n📈 Рост выручки (3 года CAGR): {data['revenue_growth']*100:.1f}%")
    if data.get('eps_growth'):
        lines.append(f"Рост EPS (3 года CAGR): {data['eps_growth']*100:.1f}%")
    
    lines.append("\n⚠️ **Риски**")
    risks = []
    if isinstance(data['debt_to_equity'], (int,float)) and data['debt_to_equity'] > 1.0:
        risks.append(f"• Высокий долг (D/E = {data['debt_to_equity']:.2f})")
    if isinstance(data['current_ratio'], (int,float)) and data['current_ratio'] < 1.0:
        risks.append(f"• Низкая ликвидность (Current Ratio = {data['current_ratio']:.2f})")
    if isinstance(data['pe'], (int,float)) and data['pe'] > 30:
        risks.append(f"• Высокий P/E ({data['pe']:.1f}) – возможна переоценка")
    if isinstance(data['peg'], (int,float)) and data['peg'] > 1.5:
        risks.append(f"• Переоцененность роста (PEG = {data['peg']:.2f})")
    if not risks:
        risks.append("• Нет очевидных финансовых красных флагов.")
    for r in risks:
        lines.append(r)
    
    lines.append("\n📌 **Вердикт**")
    if isinstance(data['peg'], (int,float)) and data['peg'] < 1.0 and isinstance(data['pe'], (int,float)) and data['pe'] < 20:
        lines.append("✅ Компания выглядит **недооцененной**. Рассмотрите покупку.")
    elif isinstance(data['peg'], (int,float)) and data['peg'] > 1.5:
        lines.append("⚠️ Акция **переоценена**. Лучше дождаться коррекции.")
    else:
        lines.append("🟡 Нейтральная оценка. Требуется ручное изучение конкурентных преимуществ.")
    
    lines.append(f"\n🔗 [Yahoo Finance](https://finance.yahoo.com/quote/{ticker})")
    return "\n".join(lines)

# -------------------------------------------------------------------
# 5. ОТПРАВКА В TELEGRAM
# -------------------------------------------------------------------

def send_to_telegram(message):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("⚠️ Нет токена или chat_id")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    if len(message) > 4096:
        message = message[:4093] + "..."
    try:
        requests.post(url, json={'chat_id': chat_id, 'text': message}, timeout=10)
        print("✅ Отправлено")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# -------------------------------------------------------------------
# 6. ОСНОВНАЯ ФУНКЦИЯ (скрининг + глубокий анализ топ-10)
# -------------------------------------------------------------------

def run_analysis():
    print(f"📊 Старт {datetime.now()}\n")
    
    # Загрузка списков
    sp500 = get_sp500_tickers()
    nasdaq100 = get_nasdaq100_tickers()
    stoxx600 = get_stoxx600_tickers()
    
    us_tickers = list(set(sp500 + nasdaq100))
    eu_tickers = stoxx600
    
    print(f"🇺🇸 США: {len(us_tickers)} тикеров")
    print(f"🇪🇺 Европа: {len(eu_tickers)} тикеров")
    
    all_results = []
    
    # Быстрый скрининг США
    print("\n🇺🇸 Сканирование США...")
    for i, t in enumerate(us_tickers):
        if i % 50 == 0:
            print(f"  {i}/{len(us_tickers)}")
        m = get_fast_metrics(t, 'US')
        if m:
            all_results.append(m)
        time.sleep(0.2)
    
    # Быстрый скрининг Европы
    print("\n🇪🇺 Сканирование Европы...")
    for i, t in enumerate(eu_tickers):
        if i % 50 == 0:
            print(f"  {i}/{len(eu_tickers)}")
        m = get_fast_metrics(t, 'EU')
        if m:
            all_results.append(m)
        time.sleep(0.2)
    
    # Сортировка
    all_results.sort(key=lambda x: x['total'], reverse=True)
    top10 = all_results[:10]
    
    # Краткий отчёт с топ-10
    brief = "="*50 + f"\n📈 ТОП-10 КАНДИДАТОВ\n" + "="*50 + "\n"
    for i, r in enumerate(top10, 1):
        brief += f"{i}. {r['ticker']} ({r['region']}) | Total: {r['total']:.1f}\n"
        if r.get('peg'):
            brief += f"   PEG: {r['peg']:.2f}  P/E: {r['pe']:.1f}  ROE: {r['roe']*100:.1f}%\n"
        else:
            brief += f"   P/E: {r['pe']:.1f}\n"
    
    # --- Добавленная статистика ---
    total_analyzed = len(all_results)
    avg_peg = np.mean([r['peg'] for r in all_results if r.get('peg')]) if total_analyzed > 0 else 0
    brief += f"\n📊 Всего проанализировано: {total_analyzed} компаний\n"
    brief += f"📊 Средний PEG среди найденных: {avg_peg:.2f}\n"
    brief += "="*50 + "\n⚠️ Не ИИР\n"
    
    send_to_telegram(brief)
    
    # Теперь для каждого из топ-10 – глубокий анализ
    for r in top10:
        ticker = r['ticker']
        print(f"\n🔍 Глубокий анализ {ticker}...")
        data, _ = get_company_info(ticker)
        deep_report = generate_deep_analysis(ticker, data)
        # Добавим заголовок, чтобы не спутать с основным отчётом
        send_to_telegram(f"🧠 *Глубокий анализ {ticker}*\n\n{deep_report}")
        time.sleep(1)  # пауза между отправками, чтобы не забанили
    
    print("\n✅ Все отчёты отправлены")

# -------------------------------------------------------------------
# 7. ЗАПУСК
# -------------------------------------------------------------------

if __name__ == "__main__":
    run_analysis()
