import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.db import SessionLocal
from app.models.document import Document
from app.agents.agent_5_table_extraction import (
    find_pl_page, extract_rows_horizontal, reconstruct_stacked_rows,
    match_financial_rows, extract_financial_table, detect_layout
)

def test():
    db = SessionLocal()
    doc = db.query(Document).order_by(Document.upload_timestamp.desc()).first()
    if not doc:
        print("No document found"); return

    print(f"Testing on: {doc.filename}")
    extracted_text = doc.extracted_text or {}
    table_text, table_page = find_pl_page(extracted_text)
    print(f"Best page: {table_page}")

    layout = detect_layout(table_text)
    print(f"Detected layout: {layout}")

    if layout == 'stacked':
        rows = reconstruct_stacked_rows(table_text)
        if len(rows) < 3:
            rows = extract_rows_horizontal(table_text)
    else:
        rows = extract_rows_horizontal(table_text)
        if len(rows) < 3:
            rows = reconstruct_stacked_rows(table_text)

    print(f"Rows with >=2 numbers found: {len(rows)}")
    print("\nTop 10 rows:")
    for r in rows[:10]:
        print(f"  label={r['label'][:50]:50s}  nums={r['numbers'][:3]}")

    mapped = match_financial_rows(rows)
    print("\n--- SEMANTIC MATCH RESULTS ---")
    for k, v in mapped.items():
        print(f"  {k:35}: {v[:3]}")

    fd = extract_financial_table(table_text, table_page)
    print("\n--- FINAL FINANCIAL DATA ---")
    for k, v in fd.items():
        print(f"  {k:35}: {v}")

if __name__ == "__main__":
    test()
