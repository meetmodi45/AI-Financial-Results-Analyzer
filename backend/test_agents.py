import sys
import os
import re
import json

# Add parent dir to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.db import SessionLocal
from app.models.document import Document

def ok(label, value, expected=None):
    status = "[OK ]"
    if value is None or value == "" or value == "None":
        status = "[-- ]"
    
    val_str = str(value)
    if expected:
        print(f"  {status} {label:35} {val_str:20} (expected ~{expected})")
    else:
        print(f"  {status} {label:35} {val_str:20}")

def fail(label, msg):
    print(f"  [ERR] {label:35} → {msg}")

SEP = "=" * 65

db = SessionLocal()
doc = db.query(Document).order_by(Document.upload_timestamp.desc()).first()

if not doc:
    print("No documents found in database.")
    sys.exit(1)

print(SEP)
print(f"  DOCUMENT : {doc.filename}")
print(f"  STATUS   : {doc.processing_status}")
print(f"  ERROR    : {doc.error_message or 'None'}")
print(SEP)

# ── AGENT 1 & 2 ─────────────────────────────────────────────────────────────
print("\n[ AGENT 1 & 2 ] Ingestion + PDF Type Classifier")
meta = doc.metadata_json or {}
ok("Pages",          meta.get('total_pages'))
ok("PDF Type",       meta.get('pdf_type'))
ok("Requires OCR",   meta.get('requires_ocr'))

# ── AGENT 3 ──────────────────────────────────────────────────────────────────
print("\n[ AGENT 3 ] OCR / Text Extraction")
text_pages = doc.extracted_text or {}
total_chars = sum(len(v) for v in text_pages.values())
ok("Pages extracted",  len(text_pages))
ok("Total chars",      f"{total_chars:,}")

# ── AGENT 4 ──────────────────────────────────────────────────────────────────
print("\n[ AGENT 4 ] Document Classification")
ok("Document category", meta.get('document_category'))

# ── AGENT 5 ──────────────────────────────────────────────────────────────────
print("\n[ AGENT 5 ] Financial Metric Extraction  (INR in crores)")
fd = doc.financial_data or {}
if not fd:
    fail("financial_data", "EMPTY — Agent 5 produced no output!")
else:
    print("  -- Income --")
    ok("Revenue from ops  Q current",  fd.get('revenue_q_current'),       "270.10")
    ok("Total income Q current",       fd.get('total_income_q_current'),   "734.72")
    
    print("  -- Profitability --")
    ok("PBT Q current",                fd.get('profit_before_tax_q_current'), "134.03")
    ok("PAT Q current",                fd.get('pat_q_current'),           "152.89")
    
    print("  -- EPS --")
    ok("Basic EPS Q",                  fd.get('basic_eps_q'),             "9.70")

    ok("Extraction confidence",        fd.get('extraction_confidence'))
    ok("Source page",                  fd.get('source_page'))

# ── AGENT 7 ──────────────────────────────────────────────────────────────────
print("\n[ AGENT 7 ] Financial Ratio Analysis")
res = doc.analysis_results or {}
ok("Net Margin %",      res.get('net_margin'))
ok("PBT Margin %",      res.get('pbt_margin'))

# ── AGENT 10 ─────────────────────────────────────────────────────────────────
print("\n[ AGENT 10 ] Visualization / Chart Data")
charts = (doc.metadata_json or {}).get('charts_data', {})
if not charts:
    fail("charts_data", "EMPTY")
else:
    for chart_name, chart in charts.items():
        if isinstance(chart, dict):
            labels = chart.get('labels', [])
            data   = chart.get('datasets', [{}])[0].get('data', [])
            ok(chart_name, list(zip(labels, data))[:3])

# ── RAW PAGE TEXT DUMP ──────────────────────────────────────────────────────
best_page = fd.get('source_page', -1)
print(f"\n[ RAW PAGE TEXT ] Page {best_page} (first 150 lines)")
if best_page >= 0:
    raw = text_pages.get(str(best_page), '')
    for i, line in enumerate(raw.split('\n')[:150]):
        if line.strip():
            print(f"  {i:3d}: {line[:120]}")

print(f"\n{SEP}")
db.close()
