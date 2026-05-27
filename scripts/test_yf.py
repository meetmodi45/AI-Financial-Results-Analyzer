import yfinance as yf

ticker = yf.Ticker("SONACOMS.NS")
info = ticker.info
keys_to_check = [
    "trailingPE", "forwardPE", "pegRatio", "priceToBook", 
    "priceToSalesTrailing12Months", "enterpriseToEbitda", 
    "dividendYield", "marketCap", "freeCashflow"
]
print("INFO KEYS RETURNED:", len(info.keys()))
for k in keys_to_check:
    print(f"{k}: {info.get(k)}")
