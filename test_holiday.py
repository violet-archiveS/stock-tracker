import FinanceDataReader as fdr
kospi = fdr.StockListing('KOSPI')
print(kospi[['Name','Close','Changes','ChagesRatio']].head(5))