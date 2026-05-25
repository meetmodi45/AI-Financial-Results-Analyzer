import io
import csv
import urllib.request

def test():
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req) as response:
        decoded_content = response.read().decode('utf-8-sig')
    
    reader = csv.DictReader(io.StringIO(decoded_content))
    added = 0
    for row in reader:
        row_dict = {str(k).strip(): v for k, v in row.items()}
        print(f"SYMBOL: {row_dict.get('SYMBOL')}, NAME: {row_dict.get('NAME OF COMPANY')}")
        added += 1
        if added > 5:
            break
test()
