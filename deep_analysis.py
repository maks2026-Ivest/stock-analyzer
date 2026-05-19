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
import sys

warnings.filterwarnings('ignore')

# -------------------------------------------------------------------
# 1. ФУНКЦИЯ ОТПРАВКИ В TELEGRAM (та же, что в основном скрипте)
# -------------------------------------------------------------------

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
        requests.post(url, json={'chat_id': chat_id, 'text': message}, timeout=10)
    except Exception as e:
        print(f"Ошибка: {e}")

# -------------------------------------------------------------------
# 2. СБОР ДАННЫХ ПО ТИКЕРУ
# -------------------------------------------------------------------

def get_company_info(ticker):
    """Собирает максимум информации о компании"""
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
        'revenue_growth': None,
        'profit_margin': info.get('profitMargins', 'N/A'),
        'operating_margin': info.get('operatingMargins', 'N/A'),
    }
    
    # Рост выручки за 3 года
    try:
        financials = stock.financials
        if 'Total Revenue' in financials.index:
            revenue = financials.loc['Total Revenue']
            if len(revenue) >= 3:
                first = revenue.iloc[-1]
                last = revenue.iloc[0]
                years = len(revenue) - 1
                data['revenue_growth'] = (last / first) ** (1/years) - 1
    except:
        pass
    
    # Рост прибыли за 3 года
    try:
        earnings = stock.earnings
        if earnings is not None and len(earnings) >= 3:
            eps = earnings['earnings']
            if len(eps) >= 3:
                first = eps.iloc[-1]
                last = eps.iloc[0]
                years = len(eps) - 1
                data['eps_growth'] = (last / first) ** (1/years) - 1
    except:
        data['eps_growth'] = None
    
    # Инсайдерские покупки/продажи (простейший proxy – изменения в holdings)
    try:
        holders = stock.institutional_holders
        if holders is not None:
            data['institutional_holders'] = len(holders)
        else:
            data['institutional_holders'] = 'N/A'
    except:
        data['institutional_holders'] = 'N/A'
    
    return data, stock

# -------------------------------------------------------------------
# 3. ГЕНЕРАЦИЯ КАЧЕСТВЕННОГО АНАЛИЗА (без ИИ – на основе метрик)
# -------------------------------------------------------------------

def generate_analysis(ticker, data):
    lines = []
    lines.append("=" * 70)
    lines.append(f"🔍 ГЛУБОКИЙ АНАЛИЗ: {ticker.upper()} – {data['name']}")
    lines.append("=" * 70)
    
    # 1. Описание бизнеса
    lines.append(f"\n🏢 **О КОМПАНИИ**")
    lines.append(f"Сектор: {data['sector']} | Индустрия: {data['industry']} | Страна: {data['country']}")
    if data['summary'] != 'Нет описания':
        summary = data['summary'][:800] + "..." if len(data['summary']) > 800 else data['summary']
        lines.append(f"\n{summary}")
    
    # 2. Ключевые финансовые показатели
    lines.append(f"\n📊 **КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ**")
    lines.append(f"Капитализация: {data['market_cap']:,}")
    lines.append(f"P/E (TTM): {data['pe']:.2f}" if isinstance(data['pe'], (int, float)) else f"P/E: {data['pe']}")
    lines.append(f"Forward P/E: {data['forward_pe']:.2f}" if isinstance(data['forward_pe'], (int, float)) else f"Forward P/E: {data['forward_pe']}")
    lines.append(f"PEG: {data['peg']:.2f}" if isinstance(data['peg'], (int, float)) else f"PEG: {data['peg']}")
    lines.append(f"P/B: {data['pb']:.2f}" if isinstance(data['pb'], (int, float)) else f"P/B: {data['pb']}")
    lines.append(f"ROE: {data['roe']*100:.1f}%" if isinstance(data['roe'], (int, float)) else f"ROE: {data['roe']}")
    lines.append(f"ROA: {data['roa']*100:.1f}%" if isinstance(data['roa'], (int, float)) else f"ROA: {data['roa']}")
    lines.append(f"Долг/Equity: {data['debt_to_equity']:.2f}" if isinstance(data['debt_to_equity'], (int, float)) else f"Долг/Equity: {data['debt_to_equity']}")
    lines.append(f"Current Ratio: {data['current_ratio']:.2f}" if isinstance(data['current_ratio'], (int, float)) else f"Current Ratio: {data['current_ratio']}")
    lines.append(f"Валовая маржа: {data['profit_margin']*100:.1f}%" if isinstance(data['profit_margin'], (int, float)) else f"Валовая маржа: {data['profit_margin']}")
    lines.append(f"Операционная маржа: {data['operating_margin']*100:.1f}%" if isinstance(data['operating_margin'], (int, float)) else f"Операционная маржа: {data['operating_margin']}")
    lines.append(f"FCF Yield: {data['fcf_yield']*100:.1f}%" if isinstance(data['fcf_yield'], (int, float)) else f"FCF Yield: {data['fcf_yield']}")
    lines.append(f"Дивидендная доходность: {data['dividend_yield']*100:.1f}%" if isinstance(data['dividend_yield'], (int, float)) else f"Дивиденды: {data['dividend_yield']}")
    lines.append(f"Beta: {data['beta']:.2f}" if isinstance(data['beta'], (int, float)) else f"Beta: {data['beta']}")
    
    # 3. Рост
    lines.append(f"\n📈 **ДИНАМИКА РОСТА**")
    if data.get('revenue_growth'):
        lines.append(f"Рост выручки (3 года CAGR): {data['revenue_growth']*100:.1f}%")
    else:
        lines.append("Рост выручки: данные недоступны")
    if data.get('eps_growth'):
        lines.append(f"Рост EPS (3 года CAGR): {data['eps_growth']*100:.1f}%")
    else:
        lines.append("Рост EPS: данные недоступны")
    
    # 4. Конкуренты (список из 5 похожих компаний через yfinance)
    lines.append(f"\n⚔️ **КОНКУРЕНТЫ**")
    try:
        competitors = yf.Ticker(ticker).info.get('competitors', [])
        if competitors:
            for c in competitors[:5]:
                lines.append(f"  - {c}")
        else:
            # Попытка найти конкурентов через сектор
            sector = data['sector']
            if sector != 'N/A':
                lines.append(f"  Сектор: {sector}. Точный список конкурентов не загрузился.")
                lines.append(f"  Рекомендуется поискать компании из индустрии: {data['industry']}")
            else:
                lines.append("  Данные о конкурентах отсутствуют в Yahoo Finance.")
    except:
        lines.append("  Не удалось загрузить список конкурентов.")
    
    # 5. Риски
    lines.append(f"\n⚠️ **ОСНОВНЫЕ РИСКИ**")
    risks = []
    if isinstance(data['debt_to_equity'], (int, float)) and data['debt_to_equity'] > 1.0:
        risks.append(f"  • Высокая долговая нагрузка (D/E = {data['debt_to_equity']:.2f})")
    if isinstance(data['current_ratio'], (int, float)) and data['current_ratio'] < 1.0:
        risks.append(f"  • Низкая ликвидность (Current Ratio = {data['current_ratio']:.2f})")
    if isinstance(data['pe'], (int, float)) and data['pe'] > 30:
        risks.append(f"  • Высокий мультипликатор P/E ({data['pe']:.1f}) – акция может быть переоценена")
    if isinstance(data['peg'], (int, float)) and data['peg'] > 1.5:
        risks.append(f"  • Переоцененность роста (PEG = {data['peg']:.2f} > 1.5)")
    if isinstance(data['beta'], (int, float)) and data['beta'] > 1.5:
        risks.append(f"  • Высокая волатильность (Beta = {data['beta']:.2f})")
    if not risks:
        risks.append("  • Нет очевидных финансовых красных флагов, но всегда есть рыночные и регуляторные риски.")
    for r in risks:
        lines.append(r)
    
    # 6. Оценка справедливой стоимости (простейшая DCF на основе FCF)
    lines.append(f"\n💰 **ПРИБЛИЗИТЕЛЬНАЯ ОЦЕНКА**")
    try:
        fcf = data['fcf_yield']
        if isinstance(fcf, (int, float)) and fcf > 0:
            fcf_yield = fcf
            # Если FCF Yield > 8% – дешево, 5-8% – норма, <5% – дорого
            if fcf_yield > 0.08:
                lines.append(f"  FCF Yield = {fcf_yield*100:.1f}% > 8% → акция выглядит НЕДООЦЕНЕННОЙ.")
            elif fcf_yield > 0.05:
                lines.append(f"  FCF Yield = {fcf_yield*100:.1f}% (5-8%) → справедливая оценка.")
            else:
                lines.append(f"  FCF Yield = {fcf_yield*100:.1f}% < 5% → акция может быть ПЕРЕОЦЕНЕНА.")
        else:
            lines.append("  FCF Yield недоступен. Используйте PEG и P/E для относительной оценки.")
    except:
        lines.append("  Недостаточно данных для автоматической оценки.")
    
    # 7. Итог
    lines.append(f"\n📌 **ИТОГОВЫЙ ВЕРДИКТ (автоматический)**")
    if (isinstance(data['peg'], (int, float)) and data['peg'] < 1.0) and (isinstance(data['pe'], (int, float)) and data['pe'] < 20):
        lines.append("  ✅ Компания выглядит НЕДООЦЕНЕННОЙ относительно роста и прибыли.")
    elif (isinstance(data['peg'], (int, float)) and data['peg'] > 1.5) or (isinstance(data['pe'], (int, float)) and data['pe'] > 30):
        lines.append("  ⚠️ Компания выглядит ПЕРЕОЦЕНЕННОЙ. Рекомендуется дождаться коррекции.")
    else:
        lines.append("  🟡 Компания справедливо оценена. Требуется ручной анализ конкурентных преимуществ.")
    
    lines.append(f"\n🔗 **ПОЛЕЗНЫЕ ССЫЛКИ**")
    lines.append(f"Yahoo Finance: https://finance.yahoo.com/quote/{ticker}")
    if data['website'] != 'N/A':
        lines.append(f"Сайт компании: {data['website']}")
    lines.append(f"Macrotrends: https://www.macrotrends.net/stocks/charts/{ticker}")
    
    lines.append("\n" + "=" * 70)
    lines.append("⚠️ Дисклеймер: анализ основан на ограниченных данных и не является инвестиционной рекомендацией.")
    lines.append("   Всегда проводите собственное исследование.")
    lines.append("=" * 70)
    
    return "\n".join(lines)

# -------------------------------------------------------------------
# 4. ОСНОВНАЯ ФУНКЦИЯ (принимает тикер как аргумент)
# -------------------------------------------------------------------

def deep_analysis(ticker):
    print(f"Запуск глубокого анализа для {ticker.upper()}...")
    data, _ = get_company_info(ticker)
    report = generate_analysis(ticker, data)
    return report

if __name__ == "__main__":
    # Если передан аргумент командной строки, используем его
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        report = deep_analysis(ticker)
        print(report)
        send_to_telegram(report)
    else:
        print("Использование: python deep_analysis.py <TICKER>")
        print("Пример: python deep_analysis.py ADBE")
