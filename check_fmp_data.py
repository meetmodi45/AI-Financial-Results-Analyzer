import os
import asyncio
import httpx
import json
from dotenv import load_dotenv

# Load FMP_API_KEY from .env
load_dotenv(".env")
FMP_API_KEY = os.getenv("FMP_API_KEY", "")

BASE_URL = "https://financialmodelingprep.com/stable"
ENDPOINTS = [
    "profile",
    "income-statement",
    "balance-sheet-statement",
    "key-metrics"
]

async def fetch_and_save(symbol: str):
    fmp_symbol = symbol
    
    # Create output directory
    out_dir = f"fmp_data_outputs/{fmp_symbol}"
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Fetching data for {fmp_symbol} using stable endpoints...")
    
    async with httpx.AsyncClient() as client:
        for endpoint in ENDPOINTS:
            url = f"{BASE_URL}/{endpoint}?symbol={fmp_symbol}&apikey={FMP_API_KEY}"
            try:
                response = await client.get(url)
                file_path = f"{out_dir}/{endpoint}.json"
                
                if response.status_code == 200:
                    data = response.json()
                    with open(file_path, "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"SUCCESS [{response.status_code}] {endpoint} -> Saved to {file_path} (Items: {len(data)})")
                else:
                    error_data = response.text
                    with open(file_path, "w") as f:
                        f.write(error_data)
                    print(f"ERROR [{response.status_code}] {endpoint} -> Error saved to {file_path}")
            except Exception as e:
                print(f"EXCEPTION on {endpoint}: {e}")

if __name__ == "__main__":
    import sys
    symbol_to_test = sys.argv[1] if len(sys.argv) > 1 else "ELLEN"
    asyncio.run(fetch_and_save(symbol_to_test))
