import FinanceDataReader as fdr
import pandas as pd

kospi = fdr.StockListing('KOSPI')
kospi['Market'] = 'KOSPI'
kosdaq = fdr.StockListing('KOSDAQ')
kosdaq['Market'] = 'KOSDAQ'
df = pd.concat([kospi, kosdaq], ignore_index=True)

df = df.rename(columns={
    'Code': 'code', 'Name': 'name', 'Market': 'market',
    'Marcap': 'mktcap', 'Volume': 'volume', 'Amount': 'amount',
    'Close': 'price', 'ChagesRatio': 'change_pct'
})

df['mktcap_억'] = (df['mktcap'].fillna(0) / 1e8).astype(int)
df['change_pct'] = df['change_pct'].fillna(0).round(2)

df_filtered = df[df['mktcap_억'] >= 1000].copy()
print(f"시가총액 1000억 이상: {len(df_filtered)}개")

upper = df_filtered[df_filtered['change_pct'] >= 29.5][['name', 'change_pct', 'mktcap_억']].sort_values('change_pct', ascending=False)
print(f"\n상한가 종목 ({len(upper)}개):")
print(upper.to_string())