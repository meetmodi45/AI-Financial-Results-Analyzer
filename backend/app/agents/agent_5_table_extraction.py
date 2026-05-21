# ==========================================================
# AGENT 5 — FINANCIAL ROW INTELLIGENCE EXTRACTION
# Layout Independent Indian Results Parser
# ==========================================================

import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import logging
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus

logger = logging.getLogger(__name__)


# ==========================================================
# STEP 1 — CLEAN NUMBER
# ==========================================================

def clean_number(token: str):
    if not token:
        return None
    token = token.strip()
    token = re.sub(r'[₹$%,]|Rs\.?', '', token)
    negative = (token.startswith("(") and token.endswith(")")) or (token.startswith("[") and token.endswith(")"))
    token = token.strip("()[]")
    # token.replace(",", "") is redundant if we include it in the re.sub above
    try:
        val = float(token)
        # Reject obvious noise: single/double digit ints (row indices, notes)
        if val == int(val) and abs(val) < 100:
            return None
        return -val if negative else val
    except:
        return None


# ==========================================================
# STEP 2A — LAYOUT DETECTION
# Detects whether table is horizontal or stacked-vertical
# ==========================================================

def detect_layout(table_text: str) -> str:
    """
    Returns 'horizontal' or 'stacked'.
    Horizontal: each P&L row has 2+ numbers on a single line.
    Stacked: numbers appear one-per-line below the label block.
    """
    lines = [l.strip() for l in table_text.split("\n") if l.strip()]
    multi_num_count = 0
    single_num_count = 0

    for line in lines:
        stripped = re.sub(r'^[|\[\]I1!l\s]+', '', line)
        nums = re.findall(r'[\d,]+\.\d+', stripped)  # find decimal numbers
        if len(nums) >= 2:
            multi_num_count += 1
        elif len(nums) == 1:
            single_num_count += 1

    # If most numeric lines have only 1 number, it's stacked
    total = multi_num_count + single_num_count
    if total == 0:
        return 'horizontal'
    stacked_ratio = single_num_count / total
    layout = 'stacked' if stacked_ratio > 0.65 else 'horizontal'
    logger.info(f"[Agent5] Layout={layout} (multi={multi_num_count}, single={single_num_count})")
    return layout


# ==========================================================
# STEP 2B — RECONSTRUCT ROWS FROM STACKED LAYOUT
# For PDFs where labels and numbers are in separate blocks
# ==========================================================

def reconstruct_stacked_rows(table_text: str):
    """
    Northern Arc / NBFC style: labels appear first, then a block of numbers.
    Each line in the number block is exactly ONE value for one time-period.
    We group N consecutive values per label (N = number of time-period columns).
    """
    lines = [
        re.sub(r'^[|\[\]I1!l\s]+', '', l).strip()
        for l in table_text.split("\n")
    ]

    # Financial label keywords — only lines with these words are true P&L labels
    _LABEL_KW = re.compile(
        r'revenue|income|sales|turnover|expense|cost|profit|loss|tax|eps|'
        r'earnings|depreciation|amortis|impairment|fee|commission|interest|'
        r'finance|employee|benefit|total|other|exceptional|comprehensive',
        re.IGNORECASE
    )
    # A true financial number: optional commas, optional decimal
    _FIN_NUM = re.compile(r'^-?\(?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\)?$|^-?\(?\d+\.\d{2,}\)?$')

    label_lines = []
    raw_number_lines = []
    label_block_done = False

    for line in lines:
        if not line:
            continue

        has_word = bool(re.search(r'[A-Za-z]{3,}', line))
        clean = line.replace(' ', '')
        is_financial_num = bool(_FIN_NUM.match(clean))

        if is_financial_num and not has_word:
            val = clean_number(clean)
            if val is not None:
                label_block_done = True
                raw_number_lines.append(val)
        elif has_word and not label_block_done:
            # Only accept lines with genuine financial vocabulary
            if _LABEL_KW.search(line):
                label_lines.append(line.strip().lower())

    n_labels = len(label_lines)
    n_numbers = len(raw_number_lines)
    if n_labels == 0 or n_numbers == 0:
        return []

    # Snap to standard Indian quarterly result column counts: 5, 4, 3, 2
    raw_ratio = n_numbers / n_labels
    for candidate in [5, 4, 3, 2]:
        if abs(raw_ratio - candidate) <= 1.5:
            n_cols = candidate
            break
    else:
        n_cols = max(1, round(raw_ratio))

    rows = []
    for i, label in enumerate(label_lines):
        start = i * n_cols
        nums = raw_number_lines[start: start + n_cols]
        if nums:
            rows.append({"label": label, "numbers": nums})

    logger.info(f"[Agent5] Stacked: {n_labels} labels, {n_numbers} values, {n_cols} cols => {len(rows)} rows")
    return rows


# ==========================================================
# STEP 2C — EXTRACT ROWS FROM INTERLEAVED LAYOUT
# ==========================================================

def extract_rows_interleaved(table_text: str):
    """
    DLF/Ceinsys style: Label is on one line, followed by its column values on subsequent lines.
    """
    lines = [l.strip() for l in table_text.split("\n") if l.strip()]
    
    _FIN_NUM = re.compile(r'^-?\(?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\)?$|^-?\(?\d+\.\d{2,}\)?$')
    _NOISE_LABELS = re.compile(r'audited|unaudited|note|particulars|quarter|year|ended', re.IGNORECASE)
    
    rows = []
    current_label = None
    current_nums = []
    
    for line in lines:
        clean = line.replace(' ', '')
        is_num = bool(_FIN_NUM.match(clean))
        
        if is_num:
            val = clean_number(clean)
            if val is not None and current_label:
                current_nums.append(val)
        else:
            # Check if it's a valid label (has words, not just noise like 'Audited')
            has_word = bool(re.search(r'[A-Za-z]{3,}', line))
            is_noise = bool(_NOISE_LABELS.search(line)) and len(line) < 15
            
            if has_word and not is_noise:
                if current_label and current_nums:
                    rows.append({"label": current_label, "numbers": current_nums})
                current_label = line.lower()
                current_nums = []
            elif has_word and is_noise:
                # If we hit noise, flush the current group but don't start a new one
                if current_label and current_nums:
                    rows.append({"label": current_label, "numbers": current_nums})
                current_label = None
                current_nums = []
                
    if current_label and current_nums:
        rows.append({"label": current_label, "numbers": current_nums})
        
    return [r for r in rows if len(r['numbers']) >= 2]


# ==========================================================
# STEP 2D — EXTRACT ROWS FROM HORIZONTAL LAYOUT
# ==========================================================

def extract_rows_horizontal(table_text: str):
    rows = []
    lines = [
        re.sub(r'^[|\[\]I1!l\s]+', '', l).strip()
        for l in table_text.split("\n")
        if l.strip()
    ]

    for line in lines:
        dec_nums = re.findall(r'-?\(?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\)?', line)
        numbers = [clean_number(n) for n in dec_nums]
        numbers = [v for v in numbers if v is not None]

        if len(numbers) >= 2:
            label = re.sub(r'-?\(?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\)?', '', line)
            label = re.sub(r'[^A-Za-z\s]', ' ', label).strip().lower()
            if len(label) > 3:
                rows.append({"label": label, "numbers": numbers})

    return rows


# ==========================================================
# STEP 3 — FINANCIAL CONCEPT ONTOLOGY
# ==========================================================

FINANCIAL_CONCEPTS = {
    "revenue_from_operations": [
        "revenue from operations",
        "income from operations",
        "net sales",
        "turnover",
        "interest income",
        "gross revenue",
        "total revenue from operations",
    ],
    "total_income": [
        "total income",
        "total revenue",
    ],
    "profit_before_tax": [
        "profit before tax",
        "profit before exceptional items and tax",
        "profit before exceptional items",
    ],
    "net_profit": [
        "net profit",
        "profit after tax",
        "profit for the period",
        "profit for the year",
        "profit after tax and minority interest",
    ],
    "basic_eps": [
        "earnings per share",
        "basic earnings per share",
        "basic eps",
        "basic in rupees",
    ]
}


# ==========================================================
# STEP 4 — BUILD TFIDF MATCHER
# ==========================================================

def build_similarity_engine(rows):
    corpus = []
    concept_lookup = []

    for concept, phrases in FINANCIAL_CONCEPTS.items():
        for p in phrases:
            corpus.append(p)
            concept_lookup.append(concept)

    for r in rows:
        corpus.append(r["label"])

    vectorizer = TfidfVectorizer(ngram_range=(1, 3)).fit(corpus)
    return vectorizer, concept_lookup


# ==========================================================
# STEP 5 — SEMANTIC MATCHING (NO REGEX DEPENDENCE)
# ==========================================================

def match_financial_rows(rows):
    if not rows:
        return {}

    vectorizer, concept_lookup = build_similarity_engine(rows)

    concept_vectors = vectorizer.transform([
        p
        for phrases in FINANCIAL_CONCEPTS.values()
        for p in phrases
    ])

    # Store best match for each concept
    best_matches = {} # concept -> (numbers, score)

    for row in rows:
        row_vec = vectorizer.transform([row["label"]])
        similarity = cosine_similarity(row_vec, concept_vectors)[0]

        best_idx = int(np.argmax(similarity))
        score = float(similarity[best_idx])

        if score < 0.25:
            continue

        concept = concept_lookup[best_idx]
        
        if concept not in best_matches or score > best_matches[concept][1]:
            best_matches[concept] = (row["numbers"], score)
            logger.info(f"[Agent5] New best match for '{concept}': '{row['label']}' (score={score:.2f})")

    return {concept: data[0] for concept, data in best_matches.items()}


# ==========================================================
# STEP 6 — COLUMN VALUE ACCESSOR
# ==========================================================

def get_value(mapped, field, index):
    row = mapped.get(field, [])
    return row[index] if index < len(row) else None


# ==========================================================
# STEP 7 — MAIN EXTRACTION FUNCTION
# ==========================================================

def extract_financial_table(table_text: str, table_page: int):
    layout = detect_layout(table_text)

    if layout == 'stacked':
        rows = reconstruct_stacked_rows(table_text)
        # Suspiciously high column count usually means it's interleaved, not block-stacked
        n_cols_detected = len(rows[0]['numbers']) if rows else 0
        if n_cols_detected > 6 or len(rows) < 3:
            logger.info(f"[Agent5] Stacked n_cols={n_cols_detected} is suspicious. Trying interleaved fallback.")
            rows = extract_rows_interleaved(table_text)
        if len(rows) < 3:
            rows = extract_rows_horizontal(table_text)
    else:
        rows = extract_rows_horizontal(table_text)
        if len(rows) < 3:
            rows = extract_rows_interleaved(table_text)
        if len(rows) < 3:
            rows = reconstruct_stacked_rows(table_text)

    if not rows:
        raise ValueError("No financial rows detected")

    mapped = match_financial_rows(rows)

    # Detect Scale (Lakhs vs Crores)
    scale_factor = 1.0
    text_lower = table_text.lower()
    if 'lakh' in text_lower:
        scale_factor = 0.01
        logger.info("[Agent5] Unit detected: Lakhs. Scaling to Crores (x0.01)")
    elif 'million' in text_lower:
        scale_factor = 0.1
        logger.info("[Agent5] Unit detected: Millions. Scaling to Crores (x0.1)")
    elif 'thousand' in text_lower:
        scale_factor = 0.0001
        logger.info("[Agent5] Unit detected: Thousands. Scaling to Crores (x0.0001)")
    
    # Apply scaling to all extracted rows
    for concept in mapped:
        mapped[concept] = [v * scale_factor for v in mapped[concept]]

    financial_data = {
        # Current Quarter (Index 0)
        "revenue_q_current": get_value(mapped, "revenue_from_operations", 0),
        "total_income_q_current": get_value(mapped, "total_income", 0),
        "profit_before_exceptional_q_current": get_value(mapped, "profit_before_tax", 0),
        "profit_before_tax_q_current": get_value(mapped, "profit_before_tax", 0),
        "pat_q_current": get_value(mapped, "net_profit", 0),
        "basic_eps_q": get_value(mapped, "basic_eps", 0),

        # Previous Quarter (Index 1)
        "revenue_q_prev": get_value(mapped, "revenue_from_operations", 1),
        "total_income_q_prev": get_value(mapped, "total_income", 1),
        "profit_before_exceptional_q_prev": get_value(mapped, "profit_before_tax", 1),
        "profit_before_tax_q_prev": get_value(mapped, "profit_before_tax", 1),
        "pat_q_prev": get_value(mapped, "net_profit", 1),

        # Quarter Year-Ago (Index 2)
        "revenue_q_year_ago": get_value(mapped, "revenue_from_operations", 2),
        "total_income_q_year_ago": get_value(mapped, "total_income", 2),
        "pat_q_year_ago": get_value(mapped, "net_profit", 2),

        # Full Year Current (Index 3)
        "revenue_fy_current": get_value(mapped, "revenue_from_operations", 3),
        "total_income_fy_current": get_value(mapped, "total_income", 3),
        "profit_before_exceptional_fy_current": get_value(mapped, "profit_before_tax", 3),
        "profit_before_tax_fy_current": get_value(mapped, "profit_before_tax", 3),
        "pat_fy_current": get_value(mapped, "net_profit", 3),

        # Full Year Previous (Index 4)
        "revenue_fy_prev": get_value(mapped, "revenue_from_operations", 4),
        "total_income_fy_prev": get_value(mapped, "total_income", 4),
        "profit_before_exceptional_fy_prev": get_value(mapped, "profit_before_tax", 4),
        "profit_before_tax_fy_prev": get_value(mapped, "profit_before_tax", 4),
        "pat_fy_prev": get_value(mapped, "net_profit", 4),

        "source_page": table_page,
        "extraction_confidence": "high" if get_value(mapped, "net_profit", 0) else "low",
    }

    return {k: v for k, v in financial_data.items() if v is not None}


# ==========================================================
# PAGE IDENTIFICATION SIGNALS
# ==========================================================

_PL_SIGNALS = [
    (3, r'revenue\s+from\s+op(?:eration)?s?'),
    (3, r'income\s+from\s+op(?:eration)?s?'),
    (3, r'net\s+(?:sales|turnover)'),
    (3, r'net\s+pr\w{2,4}it\s+(?:for|after)'),
    (3, r'pr\w{2,4}it\s+after\s+tax'),
    (2, r'quarter(?:\s+ended)?'),
    (2, r'year(?:\s+ended)?'),
    (2, r'total\s+income'),
    (2, r'total\s+revenue'),
    (2, r'pr\w{2,4}it\s+before\s+(?:tax|exceptional)'),
    (1, r'exceptional\s+items'),
    (1, r'earnings\s+per\s+(?:equity\s+)?share'),
    (1, r'basic\s*(?:[(<])'),
    (1, r'particulars'),
]


def find_pl_page(extracted_text: dict):
    best_page, best_score, best_text = -1, -999, ''
    for i, text in extracted_text.items():
        t = text.lower()
        score = sum(w for w, pat in _PL_SIGNALS if re.search(pat, t))
        
        # Penalize auditor reports and notes which contain dense financial terms but aren't tables
        if 'independent auditor' in t or 'we have audited' in t or 'in our opinion' in t:
            score -= 20
        if 'notes to the' in t and 'statement of' not in t:
            score -= 10
            
        # Bonus for actual statement headers
        if 'statement of' in t and ('financial results' in t or 'profit and loss' in t):
            score += 15

        num_count = len(re.findall(r'\d+', t))
        if num_count > 100:
            score += 2
            
        if score > best_score:
            best_score, best_page, best_text = score, int(i), text
    return best_text, best_page


# ==========================================================
# CELERY TASK — CALLED BY AGENT 4
# ==========================================================

def process_tables(document_id: str):
    db = SessionLocal()
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record:
        return
    try:
        doc_record.processing_status = ProcessingStatus.TABLE_EXTRACTION
        db.commit()

        extracted_text = doc_record.extracted_text or {}
        table_text, table_page = find_pl_page(extracted_text)
        if not table_text:
            raise ValueError("No P&L table found.")

        financial_data = extract_financial_table(table_text, table_page)

        logger.info(f"[Agent5] Final extracted: {financial_data}")
        doc_record.financial_data = financial_data
        db.commit()
        logger.info(f"Agent 5 (Table Extraction) completed for {document_id}")

    except Exception as e:
        logger.error(f"[Agent5] Error: {e}", exc_info=True)
        doc_record.processing_status = ProcessingStatus.FAILED
        db.commit()
    finally:
        db.close()