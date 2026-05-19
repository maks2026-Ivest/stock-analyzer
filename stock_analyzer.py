#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ежедневный скрининг акций США и Европы с отправкой отчёта в Telegram
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os
import requests
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ========================== КОНФИГУРАЦИЯ ==========================

# Список тикеров для анализа (можно расширять)
US_TICKERS = [
    'NVDA', 'MSFT', 'AAPL', 'GOOGL', 'META', 'AVGO', 'ORCL', 'ADBE',
    'CRM', 'INTC', 'AMD', 'IBM', 'NOW', 'PANW', 'SNPS', 'CDNS'
]

EU_TICKERS = [
    'ASML.AS', 'SAP.DE', 'IFX.DE', 'STM.PA', 'DSY.PA', 'NEM.DE',
    'PRX.AS', 'CAP.PA', 'SOON.DE', 'BN.PA'
]

# Пороговые значения для США и Европы
THRESHOLDS = {
    'US': {
        'ROE': 0.15,
        'PEG': 1.0,
        'PE': 15,
        'PB': 2.0,
        'DEBT_EQUITY': 0.5,
        'FCF_YIELD': 0.05,
        'REV_GROWTH': 0.10,
        'GROSS_MARGIN': 0.40,
    },
    'EU': {
        'ROE': 0.12,
        'PEG': 1.0,
        'PE': 12,
        'PB': 1.8,
        'DEBT_EQUITY': 0.4,
        'FCF_YIELD': 0.05,
        'REV_GROWTH': 0.07,
        'GROSS_MARGIN': 0.35,
    }
}

# ========================== ФУНКЦИИ АНАЛИЗА ==========================

def get_stock_metrics(ticker, region):
    """Получает финансовые метрики для одного тикера"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        pe = info.get('trailingPE')
        peg = info.get('pegRatio')
        pb = info.get('priceToBook')
        roe = info.get('returnOnEquity')
        gross_margin = info.get('grossMargins')
        debt_to_equity = info.get('debtToEquity')
        
        free_cashflow = info.get('freeCashflow')
        market_cap = info.get('marketCap')
        fcf_yield = free_cashflow / market_cap if free_cashflow and market_cap else None
        
        # Рост выручки (упрощённо)
        revenue_growth = None
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
        
        return {
            'ticker': ticker,
            'region': region,
            'pe': pe,
            'peg': peg,
            'pb': pb,
            'roe': roe,
            'gross_margin': gross_margin,
            'debt_to_equity': debt_to_equity,
            'fcf_yield': fcf_yield,
            'revenue_growth': revenue_growth,
            'market_cap': market_cap
        }
    except Exception as e:
        print(f"Ошибка {ticker}: {e}")
        return None

def calculate_quality_score(metrics, region):
    """Оценка качества бизнеса (0-10)"""
    th = THRESHOLDS[region]
    score = 5  # Старт с середины
    
    if metrics.get('roe') and metrics['roe'] > th['ROE']:
        score += 1.5
    elif metrics.get('roe') and metrics['roe'] > th['ROE'] * 0.7:
        score += 0.5
    
    if metrics.get('gross_margin') and metrics['gross_margin'] > th['GROSS_MARGIN']:
        score += 1.5
    
    if metrics.get('debt_to_equity') and metrics['debt_to_equity'] < th['DEBT_EQUITY']:
        score += 1.5
    elif metrics.get('debt_to_equity') and metrics['debt_to_equity'] < th['DEBT_EQUITY'] * 1.5:
        score += 0.5
    
    if metrics.get('revenue_growth') and metrics['revenue_growth'] > th['REV_GROWTH']:
        score += 1.5
    
    return min(score, 10)

def calculate_value_score(metrics, region):
    """Оценка недооценённости (0-10)"""
    th = THRESHOLDS[region]
    score = 5
    
    if metrics.get('pe') and metrics['pe'] < th['PE']:
        score += 2
    elif metrics.get('pe') and metrics['pe'] < th['PE'] * 1.3:
        score += 1
    
    if metrics.get('peg') and metrics['peg'] < th['PEG']:
        score += 2
    elif metrics.get('peg') and metrics['peg'] < th['PEG'] * 1.2:
        score += 1
    
    if metrics.get('fcf_yield') and metrics['fcf_yield'] > th['FCF_YIELD']:
        score += 1
    
    if metrics.get('pb') and metrics['pb'] < th['PB']:
        score += 1
    
    return min(score, 10)

# ========================== ОТПРАВКА В TELEGRAM ==========================

def send_to_telegram(message):
    """Отправляет сообщение в Telegram"""
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
            print(f"❌ Ошибка: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка соединения: {e}")

# ========================== ГЛАВНАЯ ФУНКЦИЯ ==========================

def run_analysis():
    """Запускает анализ всех тикеров и возвращает отчёт"""
    all_results = []
    
    print(f"📊 Анализ запущен {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Анализируем США
    print("🇺🇸 Анализ США...")
    for ticker in US_TICKERS:
        print(f"  {ticker}...")
        metrics = get_stock_metrics(ticker, 'US')
        if metrics:
            metrics['quality'] = calculate_quality_score(metrics, 'US')
            metrics['value'] = calculate_value_score(metrics, 'US')
            metrics['total'] = metrics['quality'] * 0.6 + metrics['value'] * 0.4
            all_results.append(metrics)
    
    # Анализируем Европу
    print("🇪🇺 Анализ Европы...")
    for ticker in EU_TICKERS:
        print(f"  {ticker}...")
        metrics = get_stock_metrics(ticker, 'EU')
        if metrics:
            metrics['quality'] = calculate_quality_score(metrics, 'EU')
            metrics['value'] = calculate_value_score(metrics, 'EU')
            metrics['total'] = metrics['quality'] * 0.6 + metrics['value'] * 0.4
            all_results.append(metrics)
    
    # Сортируем по total score
    all_results.sort(key=lambda x: x.get('total', 0), reverse=True)
    
    # Формируем отчёт
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append(f"📈 ОТЧЁТ ПО АКЦИЯМ | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report_lines.append("=" * 60)
    
    # Топ-10 лучших
    report_lines.append("\n🏆 ТОП КАНДИДАТОВ ДЛЯ ДАЛЬНЕЙШЕГО ИЗУЧЕНИЯ:\n")
    
    for i, r in enumerate(all_results[:10], 1):
        report_lines.append(f"{i}. {r['ticker']} ({r['region']}) | Total: {r['total']:.1f}/10")
        if r.get('peg'):
            report_lines.append(f"   PEG: {r['peg']:.2f} | P/E: {r['pe']:.1f} | ROE: {r['roe']*100:.1f}%" if r.get('roe') else f"   PEG: {r['peg']:.2f}")
        if r.get('revenue_growth'):
            report_lines.append(f"   Рост выручки: {r['revenue_growth']*100:.1f}% годовых")
        report_lines.append("")
    
    # Сигналы
    if all_results and all_results[0].get('peg') and all_results[0]['peg'] < 0.7:
        report_lines.append("🔔 СИГНАЛ: Найдены компании с PEG < 0.7 — потенциальная недооценка!")
    
    report_lines.append("\n" + "=" * 60)
    report_lines.append("⚠️ Дисклеймер: Не индивидуальная инвестиционная рекомендация.")
    report_lines.append("   Изучите бизнес самостоятельно перед принятием решения.")
    report_lines.append("=" * 60)
    
    return "\n".join(report_lines)

# ========================== ЗАПУСК ==========================

if __name__ == "__main__":
    report = run_analysis()
    print(report)
    send_to_telegram(report)
