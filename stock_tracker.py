import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import os

def get_recent_trading_day(df=None):
    """공휴일/주말 감지해서 직전 거래일 반환"""
    d = datetime.today()
    if d.hour < 16:
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)

    # 데이터가 있으면 실제 거래 여부 확인
    if df is not None:
        total_volume = df['Volume'].fillna(0).sum()
        if total_volume == 0:
            print(f"{d.strftime('%Y%m%d')} 거래 없음 (공휴일 추정) → 직전 거래일로 이동")
            d -= timedelta(days=1)
            while d.weekday() >= 5:
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

def run():
    print("코스피 불러오는 중...")
    kospi = fdr.StockListing('KOSPI')
    kospi['Market'] = 'KOSPI'

    print("코스닥 불러오는 중...")
    kosdaq = fdr.StockListing('KOSDAQ')
    kosdaq['Market'] = 'KOSDAQ'

    df = pd.concat([kospi, kosdaq], ignore_index=True)

    # 공휴일 감지
    date = get_recent_trading_day(df)
    print(f"{date} 기준으로 처리합니다.")

    df = df.rename(columns={
        'Code': 'code', 'Name': 'name', 'Market': 'market',
        'Marcap': 'mktcap', 'Volume': 'volume', 'Amount': 'amount',
        'Close': 'price', 'Changes': 'change'
    })

    if 'change' not in df.columns:
        df['change'] = 0.0
    if 'price' not in df.columns:
        df['price'] = 0

    df['mktcap_억'] = (df['mktcap'].fillna(0) / 1e8).astype(int)
    df['volume_만주'] = (df['volume'].fillna(0) / 1e4).round(1)
    df['amount_억'] = (df['amount'].fillna(0) / 1e8).astype(int)
    df['change_pct'] = (df['change'].fillna(0) * 100).round(2)
    df['price'] = df['price'].fillna(0).astype(int)

    # 컬럼명 확인 (디버깅용)
    print("컬럼 목록:", df.columns.tolist())
    print(f"전체 종목수: {len(df)}")
    print(f"거래량 합계: {df['volume_만주'].sum():,.0f}만주")

    # 시가총액 1000억 이상 필터
    df_filtered = df[df['mktcap_억'] >= 1000].copy()
    print(f"시가총액 1000억 이상: {len(df_filtered)}개")

    # 특징주 필터 - 실제 거래가 있는 날만 의미있는 값
    upper = set(df_filtered[df_filtered['change_pct'] >= 29.5]['code'])
    high_vol = set(df_filtered[df_filtered['volume_만주'] >= 1000]['code'])
    high_amt = set(df_filtered[df_filtered['amount_억'] >= 500]['code'])

    print(f"상한가: {len(upper)}개 / 거래량: {len(high_vol)}개 / 거래대금: {len(high_amt)}개")

    featured_codes = upper | high_vol | high_amt
    featured = df_filtered[df_filtered['code'].isin(featured_codes)].copy()
    print(f"특징주 총: {len(featured)}개")

    # 특징주가 여전히 너무 많으면 경고
    if len(featured) > 100:
        print("⚠️  특징주가 100개 초과 — 공휴일이거나 데이터 이상 가능성 있음")
        print("거래량 상위 50개만 처리합니다.")
        featured = featured.nlargest(50, 'volume_만주')

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

    # data 폴더에 JSON 저장
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

    # GitHub push
    os.system('git add .')
    os.system(f'git commit -m "Update {date}"')
    os.system('git push origin main')
    print("✓ GitHub 업로드 완료")

if __name__ == '__main__':
    run()