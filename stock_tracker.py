import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import os
import sys
import holidays

def get_trading_day(date_str=None):
    """직전 거래일 계산 (공휴일/주말 제외)"""
    kr_holidays = holidays.SouthKorea(years=datetime.today().year)
    
    if date_str:
        d = datetime.strptime(date_str, '%Y%m%d')
    else:
        d = datetime.today()
    
    while d.date().weekday() >= 5 or d.date() in kr_holidays:
        d -= timedelta(days=1)
    
    return d.strftime('%Y%m%d')

def get_news(name):
    try:
        query = requests.utils.quote(name + ' 특징주')
        url = f'https://finance.naver.com/news/news_search.naver?q={query}'
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.articleSubject a')[:3]
        return [{'title': i.text.strip(), 'url': i.get('href', '#')} for i in items]
    except:
        return []

def run(date_str=None):
    date = get_trading_day(date_str)
    print(f"거래일: {date}")

    print("코스피 불러오는 중...")
    kospi = fdr.StockListing('KOSPI')
    kospi['Market'] = 'KOSPI'

    print("코스닥 불러오는 중...")
    kosdaq = fdr.StockListing('KOSDAQ')
    kosdaq['Market'] = 'KOSDAQ'

    df = pd.concat([kospi, kosdaq], ignore_index=True)

    df = df.rename(columns={
        'Code': 'code',
        'Name': 'name',
        'Market': 'market',
        'Marcap': 'mktcap',
        'Volume': 'volume',
        'Amount': 'amount',
        'Close': 'price',
        'ChagesRatio': 'change_pct'
    })

    df['mktcap_억'] = (df['mktcap'].fillna(0) / 1e8).astype(int)
    df['volume_만주'] = (df['volume'].fillna(0) / 1e4).round(1)
    df['amount_억'] = (df['amount'].fillna(0) / 1e8).astype(int)
    df['change_pct'] = df['change_pct'].fillna(0).round(2)
    df['price'] = df['price'].fillna(0).astype(int)

    print(f"전체 종목수: {len(df)}")

    # 시가총액 1000억 이상
    df_filtered = df[df['mktcap_억'] >= 1000].copy()
    print(f"시가총액 1000억 이상: {len(df_filtered)}개")

    # 특징주 필터
    upper = set(df_filtered[df_filtered['change_pct'] >= 29.5]['code'])
    high_vol = set(df_filtered[df_filtered['volume_만주'] >= 1000]['code'])
    high_amt = set(df_filtered[df_filtered['amount_억'] >= 500]['code'])

    print(f"상한가: {len(upper)}개 / 거래량: {len(high_vol)}개 / 거래대금: {len(high_amt)}개")

    featured_codes = upper | high_vol | high_amt
    featured = df_filtered[df_filtered['code'].isin(featured_codes)].copy()
    print(f"특징주 총: {len(featured)}개")

    print(f"뉴스 수집 중... ({len(featured)}개 종목)")
    stocks = []
    for i, (_, row) in enumerate(featured.iterrows()):
        print(f"  [{i+1}/{len(featured)}] {row['name']}")
        news = get_news(row['name'])
        stocks.append({
            'code': str(row['code']),
            'name': str(row['name']),
            'market': str(row['market']),
            'price': int(row['price']),
            'change': float(row['change_pct']),
            'volume': float(row['volume_만주']),
            'amount': int(row['amount_억']),
            'mktcap': int(row['mktcap_억']),
            'news': news
        })

    # JSON 저장
    os.makedirs('data', exist_ok=True)
    json_path = f'data/{date}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({'date': date, 'stocks': stocks}, f, ensure_ascii=False)
    print(f"✓ {json_path} 저장 완료 ({len(stocks)}개 종목)")

    # 날짜 목록 업데이트
    dates_path = 'data/dates.json'
    if os.path.exists(dates_path):
        with open(dates_path, 'r', encoding='utf-8') as f:
            dates = json.load(f)
    else:
        dates = []
    if date not in dates:
        dates.append(date)
        dates.sort(reverse=True)
    with open(dates_path, 'w', encoding='utf-8') as f:
        json.dump(dates, f)
    print(f"✓ dates.json 업데이트 완료")

    # 잘못된 날짜 파일 정리
    wrong_date = datetime.today().strftime('%Y%m%d')
    if wrong_date != date:
        wrong_path = f'data/{wrong_date}.json'
        if os.path.exists(wrong_path):
            os.remove(wrong_path)
            print(f"✓ 잘못된 날짜 파일 {wrong_path} 삭제")

    # GitHub push
    os.system('git add .')
    os.system(f'git commit -m "Update {date}"')
    os.system('git push origin main')
    print("✓ GitHub 업로드 완료")

if __name__ == '__main__':
    # 날짜 인자 받기 (예: python stock_tracker.py 20260504)
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(date_arg)
