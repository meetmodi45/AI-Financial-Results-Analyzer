import asyncio
import json
from app.services.fmp_client import fetch_indianapi_data
from app.core.db import SessionLocal

async def main():
    db = SessionLocal()
    res = await fetch_indianapi_data('RELIANCE', db)
    print(json.dumps(res.get('keyMetrics', {}).get('priceandVolume', []), indent=2))
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
