
import sys, re
sys.path.append('.')
from app.agents.agent_5_table_extraction import extract_rows_interleaved, clean_number

text = """
   17: I.
   18: Revenue From Operations
   19: 16,351
   20: 16,353
   21: 13,814
   22: 63,517
   23: 39,973
   24: II.
   25: Other Income
   26: 350
   27: 334
   28: 336
   29: 2,492
   30: 2,587
   31: Ill.
   32: Total Income (I+ II)
   33: 16,701
   34: 16,687
   35: 14,150
   36: 66,009
   37: 42,560
"""
# Clean the line numbers
lines = []
for l in text.strip().split('\n'):
    if ':' in l:
        lines.append(l.split(':', 1)[1].strip())
    else:
        lines.append(l.strip())

clean_text = '\n'.join(lines)
rows = extract_rows_interleaved(clean_text)
for r in rows:
    print(f"Label: {r['label']} | Nums: {r['numbers']}")
