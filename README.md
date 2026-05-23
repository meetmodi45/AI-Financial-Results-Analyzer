# AI-Powered Financial Statements & Transcript Analyzer

An end-to-end, fully autonomous AI platform to ingest, parse, validate, and analyze corporate financial PDFs and earnings call transcripts. Converts raw financial data into structured insights, generates investment verdicts, and provides interactive visualizations for retail investors.

**Timeline**: May 2026 - Jun 2026

## 🎯 Key Features

### Financial Statement Analysis
- **10-Agent Sequential Workflow**: Intelligent pipeline that validates PDF structure, extracts financial data, and converts raw corporate statements into 60+ predefined numerical metrics via LLM-powered extraction
- **Comprehensive Financial Metrics**: Extracts and computes revenue growth (QoQ/YoY), profit margins (Net/PBT/EBITDA), balance sheet ratios, working capital metrics, and cash flow analysis
- **Multi-Currency Support**: Auto-detects and normalizes financial figures from Lakh, Million, Thousand, or other currency scales
- **Investment Verdict System**: Random Forest ML model analyzes extracted metrics to generate buy/sell/neutral recommendations with confidence scores

### Earnings Call & Transcript Analysis
- **RAG Pipeline**: LangChain + Pinecone Vector DB integration to chunk, embed, and retrieve top-5 relevant context segments from uploaded transcripts
- **Semantic Search**: Conversational AI chatbot answers earnings call queries by retrieving context-grounded information
- **Multi-Modal Input**: Supports both PDF and text file uploads for transcript analysis

### User Interface
- **Neo-Brutalist Design**: Clean, minimalist dark-mode dashboard with bold typography and high contrast
- **Real-Time Processing Pipeline**: Visual status tracker showing 10-stage agent execution with inline progress indicators
- **Interactive Financial Charts**: Recharts visualizations for revenue trends, profit analysis, and margin movements
- **Dual Analysis Tabs**: Switch between Results Analysis (PDFs) and Earnings Calls (transcripts) seamlessly
- **AI Assistant Sidebar**: General-purpose chatbot for financial concepts and analysis doubts

## 🏗️ Architecture

### Tech Stack
- **Backend**: Python FastAPI, SQLAlchemy ORM
- **LLM Integration**: LangChain, Groq API (fast, cost-effective inference)
- **Vector Database**: Pinecone (semantic search for earnings calls)
- **Message Queue**: Celery + Redis
- **Database**: PostgreSQL 15
- **ML/Data**: Scikit-Learn, XGBoost, PyMuPDF, Tesseract OCR, PDFPlumber, OpenCV, NLTK, spaCy
- **Frontend**: React 19 + Vite, TailwindCSS, Recharts, Axios, Lucide Icons
- **Containerization**: Docker Compose

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         React Frontend                           │
│  (Vite + React 19 + TailwindCSS + Recharts)                     │
│  • File Upload (Drag & Drop)                                    │
│  • Real-Time Pipeline Status Tracker                            │
│  • Financial Charts & Metrics Dashboard                         │
│  • Earnings Call Chat Interface                                 │
│  • AI Assistant Chatbot                                         │
└────────────────┬────────────────────────────────────────────────┘
                 │ REST API (localhost:8000)
┌────────────────▼────────────────────────────────────────────────┐
│                    FastAPI Backend                               │
├────────────────────────────────────────────────────────────────┤
│  Agents (Sequential Processing Pipeline)                        │
│  ├─ Agent 2: PDF Type Classifier (Text vs Scanned)             │
│  ├─ Agent 3: OCR & Text Extraction                             │
│  ├─ Agent 4: Financial Document Verification                  │
│  ├─ Agent 5: Financial Table Extraction                        │
│  ├─ Agent 6: Currency Normalization (INR Conversion)           │
│  ├─ Agent 7: Financial Ratio Analysis & Calculations           │
│  ├─ Agent 8: LLM-Powered AI Summarization (Groq)              │
│  ├─ Agent 9: ML-Based Investment Verdict (Random Forest)       │
│  ├─ Agent 10: JSON Dashboard Prep & Visualization              │
│  └─ Concall: RAG Pipeline for Transcript Analysis              │
├────────────────────────────────────────────────────────────────┤
│  Data Layer                                                      │
│  ├─ PostgreSQL: Document metadata, processing status            │
│  ├─ Redis: Task queue & caching                                │
│  └─ Pinecone: Vector embeddings for semantic search            │
└────────────────────────────────────────────────────────────────┘
```

## 📊 Processing Pipeline

### Financial Statement Processing (10-Stage Pipeline)

```
1. UPLOADED
   ↓
2. CLASSIFYING_PDF (Agent 2)
   └─ Detects: Text PDF | Scanned PDF | Hybrid
   └─ ⚠️ Scanned PDFs are rejected (current model optimized for text)
   ↓
3. OCR_EXTRACTION (Agent 3)
   └─ Extracts text using PyMuPDF + Tesseract
   ↓
4. DOCUMENT_CLASSIFICATION (Agent 4)
   └─ Verifies financial document type
   ↓
5. TABLE_EXTRACTION (Agent 5)
   └─ Extracts balance sheets, P&L, cash flow statements
   ↓
6. NORMALIZING_METRICS (Agent 6)
   └─ Converts all figures to ₹ Crores (INR normalization)
   ↓
7. FINANCIAL_ANALYSIS (Agent 7)
   └─ Calculates 60+ metrics:
      • Growth Rates: QoQ, YoY (Revenue & Profit)
      • Margins: Net %, PBT %, EBITDA %
      • Balance Sheet: Current Ratio, Debt Levels, Working Capital
      • Cash Flow: Operating CF, CapEx, Free Cash Flow
      • Efficiency: Inventory Days, Debtor Days, Cash Cycle
   ↓
8. NLP_SUMMARIZATION (Agent 8)
   └─ Groq LLM generates retail-investor friendly summary
      • Executive Overview
      • Key Highlights
      • Potential Risks
      • Investor Explanation
   ↓
9. VERDICT_PREDICTION (Agent 9)
   └─ Random Forest model predicts: GOOD | BAD | NEUTRAL
      • Confidence score (0-100%)
   ↓
10. VISUALIZATION_PREP (Agent 10)
    └─ Prepares JSON for interactive charts
    ↓
COMPLETED
```

### Earnings Call Analysis (RAG Pipeline)

```
1. FILE UPLOAD
   ├─ PDF → Text extraction
   └─ TXT → Direct ingestion
   ↓
2. VECTOR CHUNKING
   └─ Split into ~500-char semantic chunks
   ↓
3. EMBEDDING & UPSERT
   └─ Sentence-Transformers → Pinecone Vector DB
   ↓
4. SEMANTIC CHAT
   └─ User query → Embed → Find top-5 relevant chunks
   └─ LangChain + Groq → Generate grounded response
   ↓
CHAT COMPLETE
```

## 📈 Extracted Financial Metrics (60+)

### Profitability & Growth
- `qoq_growth` - Quarter-on-Quarter revenue growth %
- `yoy_growth` - Year-on-Year revenue growth %
- `pat_qoq` - Net profit QoQ growth %
- `pat_yoy` - Net profit YoY growth %
- `eps_qoq` - Earnings per share QoQ growth %
- `eps_yoy` - Earnings per share YoY growth %

### Margins
- `net_margin` - Net profit margin %
- `pbt_margin` - Profit before tax margin %
- `ebitda_margin` - EBITDA margin % (proxy calculation)
- Annual variants: `net_margin_fy`, `pbt_margin_fy`, `ebitda_margin_fy`

### Balance Sheet
- `total_borrowings_cr` - Total debt (₹ crores)
- `net_debt_cr` - Net debt (Debt - Cash)
- `current_ratio` - Liquidity indicator (Current Assets / Current Liabilities)
- `trade_receivables_cr` - Outstanding receivables
- `inventories_cr` - Inventory levels
- `cwip_cr` - Capital work-in-progress (expansion proxy)

### Cash Flow & Efficiency
- `operating_cash_flow_cr` - Cash generated from operations
- `free_cash_flow_cr` - FCF (OCF - CapEx)
- `capex_cr` - Capital expenditure
- `inventory_days` - How long inventory sits (days)
- `debtor_days` - How long to collect payments (days)

### Absolute Figures (₹ Crores)
- `total_income_q_cr` - Quarterly revenue
- `total_income_fy_cr` - Annual revenue
- `pat_q_current_cr` - Quarterly net profit
- `pat_fy_current_cr` - Annual net profit
- `basic_eps` - Earnings per share

## 🚀 Running Locally (Docker Compose)

### Prerequisites
- Docker & Docker Compose installed
- `.env` file with API keys

### 1. Create `.env` file in root directory

```bash
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_SERVER=db
POSTGRES_DB=financial_analyzer

# Redis
REDIS_URL=redis://redis:6379/0

# LLM APIs
GROQ_API_KEY=your_groq_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=financial-reports-index
```

### 2. Start the Stack

```bash
# Start database & message broker
docker-compose up -d

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Run FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Run Celery Worker (in a separate terminal)

```bash
cd backend
celery -A app.core.celery_app worker --loglevel=info -Q main-queue
```

### 4. Start the Frontend (in another terminal)

```bash
cd frontend
npm install
npm run dev
# Frontend will be available at http://localhost:5173
```

### 5. Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)

---

## 🌐 Deployment Guide (Production)

This guide deploys to **Vercel** (Frontend) and **Render** (Backend Infrastructure).

### Prerequisites
- GitHub repository connected to Vercel & Render
- Groq API key (free tier available)
- Pinecone account (free tier: 100k vectors)

### Step 1: Deploy Database & Redis (Render)

1. Go to [Render.com](https://render.com)
2. Create a **New PostgreSQL Database**
   - Note the internal and external connection URLs
3. Create a **New Redis Database**
   - Note the internal connection URL (for backend communication)

### Step 2: Deploy Backend APIs & Celery Workers (Render)

#### 2.1 Deploy Web Service (FastAPI)

1. Create a **New Web Service** on Render
2. Connect your GitHub repository
3. Configure settings:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**:
     ```
     POSTGRES_USER=postgres
     POSTGRES_PASSWORD=<your_db_password>
     POSTGRES_SERVER=<render_postgres_internal_url>
     POSTGRES_DB=financial_analyzer
     REDIS_URL=<render_redis_internal_url>
     GROQ_API_KEY=<your_groq_key>
     PINECONE_API_KEY=<your_pinecone_key>
     PINECONE_INDEX_NAME=financial-reports-index
     ```
4. Click **Deploy**

#### 2.2 Deploy Celery Worker (Background Service)

1. Create a **New Background Worker** on Render
2. Point to the same repository with root directory `backend`
3. **Start Command**:
   ```bash
   celery -A app.core.celery_app worker --loglevel=info -Q main-queue
   ```
4. Add the **same Environment Variables** so the worker can connect to DB & Redis
5. Click **Deploy**

### Step 3: Deploy Frontend (Vercel)

1. Go to [Vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Configure settings:
   - **Framework**: Vite (auto-detected)
   - **Root Directory**: `frontend`
4. **Critical Step**: Update API Base URL
   - Open `frontend/src/App.jsx`
   - Find: `const API_BASE = 'http://localhost:8000/api/v1'`
   - Replace with your Render API URL: `const API_BASE = 'https://your-api.onrender.com/api/v1'`
   - *Alternative*: Use environment variables (`frontend/.env.production`):
     ```
     VITE_API_BASE=https://your-api.onrender.com/api/v1
     ```
     Then import: `const API_BASE = import.meta.env.VITE_API_BASE`
5. Click **Deploy**

### Step 4: Verify Production Deployment

1. Test the live frontend at `https://your-app.vercel.app`
2. Upload a sample financial PDF to test the pipeline
3. Monitor logs on Render dashboard for any errors

---

## 🧠 ML Model Training

If you need to retrain the **Investment Verdict model** (Random Forest):

1. Navigate to: `backend/training/`
2. Run the training script:
   ```bash
   python train_verdict_model.py
   ```
3. The new model weights will be saved to the agents directory
4. Restart the Celery worker to load updated weights:
   ```bash
   celery -A app.core.celery_app worker --loglevel=info -Q main-queue
   ```

---

## 📁 Project Structure

```
AI-Financial-Results-Analyzer/
├── backend/
│   ├── app/
│   │   ├── main.py                          # FastAPI entry point
│   │   ├── agents/                          # 10-agent pipeline modules
│   │   │   ├── agent_2_pdf_type.py         # PDF type classifier
│   │   │   ├── agent_3_ocr.py              # OCR & text extraction
│   │   │   ├── agent_4_classifier.py       # Document verification
│   │   │   ├── agent_5_table_extraction.py # Financial data extraction
│   │   │   ├── agent_6_normalization.py    # Currency normalization
│   │   │   ├── agent_7_analysis.py         # Financial calculations (60+ metrics)
│   │   │   ├── agent_8_llm_summary.py      # LLM-powered summaries
│   │   │   ├── agent_9_verdict.py          # ML-based investment verdict
│   │   │   └── agent_10_visualization.py   # Dashboard prep
│   │   ├── api/
│   │   │   ├── routes.py                   # Document upload & status endpoints
│   │   │   ├── concall.py                  # Earnings call RAG API
│   │   │   └── assistant.py                # Global AI assistant endpoint
│   │   ├── core/
│   │   │   ├── config.py                   # Settings & environment variables
│   │   │   ├── db.py                       # SQLAlchemy database setup
│   │   │   ├── pipeline.py                 # Orchestrates all 10 agents
│   │   │   └── celery_app.py              # Celery task queue configuration
│   │   ├── models/
│   │   │   ├── base.py                     # SQLAlchemy declarative base
│   │   │   ├── document.py                 # Document model (11 JSON columns)
│   │   │   └── concall.py                  # Earnings call transcript model
│   │   └── services/
│   ├── requirements.txt                    # Python dependencies
│   ├── scripts/
│   └── training/
│       └── train_verdict_model.py          # Random Forest training script
├── frontend/
│   ├── src/
│   │   ├── App.jsx                         # Main React component (68KB)
│   │   ├── main.jsx                        # React entry point
│   │   ├── App.css                         # Brutalist styling
│   │   ├── index.css                       # Global styles
│   │   ├── components/
│   │   │   └── GlobalAssistant.jsx         # AI chatbot sidebar
│   │   └── assets/
│   ├── package.json                        # Frontend dependencies
│   ├── package-lock.json
│   ├── vite.config.js                      # Vite build configuration
│   ├── tailwind.config.js                  # TailwindCSS configuration
│   ├── postcss.config.js
│   ├── eslint.config.js
│   ├── index.html
│   └── .gitignore
├── docker-compose.yml                      # Local development stack
├── .env.example                            # Environment variable template
├── .gitignore
└── README.md
```

---

## 🔌 API Endpoints

### Financial Statement Analysis

```bash
# Upload a financial PDF (triggers 10-agent pipeline)
POST /api/v1/upload
Content-Type: multipart/form-data
Body: file (PDF)

Response:
{
  "document_id": "uuid-string",
  "filename": "earnings_report.pdf",
  "file_size": 2500000,
  "total_pages": 45,
  "status": "UPLOADED"
}
```

```bash
# Get document processing status & results
GET /api/v1/status/{document_id}

Response:
{
  "status": "COMPLETED",
  "metadata": {
    "pdf_type": "text_pdf",
    "total_pages": 45,
    "requires_ocr": false,
    "document_category": "Quarterly Financial Results",
    "charts_data": { ... }
  },
  "analysis_results": {
    "qoq_growth": 12.5,
    "yoy_growth": 18.3,
    "net_margin": 15.4,
    "current_ratio": 1.85,
    "free_cash_flow_cr": 450.2,
    ... (60+ metrics)
  },
  "nlp_summary": {
    "executive_summary": ["...", "..."],
    "investor_explanation": ["...", "..."],
    "highlights": ["..."],
    "risks": ["..."]
  },
  "verdict": {
    "verdict": "GOOD",
    "confidence": 0.87
  },
  "error_message": null
}
```

### Earnings Call Analysis

```bash
# Upload transcript and initiate RAG chunking
POST /api/v1/concall/upload-and-process
Content-Type: multipart/form-data
Body: file (PDF or TXT)

Response:
{
  "document_id": "uuid-string",
  "status": "PENDING"
}
```

```bash
# Chat with earnings call transcript
POST /api/v1/concall/chat
Content-Type: application/json
Body:
{
  "document_id": "uuid-string",
  "query": "What was the company's revenue guidance for next quarter?"
}

Response:
{
  "answer": "Based on the earnings call transcript, the company guided...",
  "sources": [
    "...(top-5 retrieved context chunks)..."
  ]
}
```

```bash
# Get concall processing status
GET /api/v1/concall/status/{document_id}

Response:
{
  "status": "COMPLETED",
  "error_message": null
}
```

---

## 🎨 UI Features

### Results Analysis Tab
- **Upload Panel**: Drag-and-drop or click to upload financial PDFs
- **Real-Time Status Tracker**: Visual display of all 10 processing stages
- **Quick Metrics**: QoQ Growth, YoY Growth, Net Margin, PAT QoQ/YoY, EPS YoY
- **Financial Charts**:
  - Revenue Trend (Quarterly)
  - Net Profit (PAT) Trend
  - Margin Trends (Net & EBITDA)
- **Analyst Summary**:
  - Executive Overview
  - Retail Investor Context
  - Key Highlights & Risks
- **Balance Sheet Profile**: Solvency, liquidity, and efficiency metrics
- **Cash Flow Statement**: Operating, investing, and financing cash flows
- **Investment Verdict**: Buy/Sell/Neutral recommendation with confidence score

### Earnings Calls Tab
- **Transcript Upload**: PDF or TXT file support
- **Semantic Chat Interface**: Ask questions about the earnings call
- **Context-Grounded Responses**: Answers backed by top-5 relevant transcript segments
- **Real-Time Vector Chunking**: Visual progress during Pinecone ingestion

### Global AI Assistant
- **Sidebar Chatbot**: General-purpose financial knowledge Q&A
- **Neo-Brutalist Design**: Integrated with main dashboard aesthetic
- **Context-Aware**: Can discuss concepts from loaded documents

---

## ⚙️ Configuration & Environment Variables

### Required Environment Variables

```env
# PostgreSQL Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_SERVER=localhost
POSTGRES_DB=financial_analyzer

# Redis Message Broker
REDIS_URL=redis://localhost:6379/0

# LLM & Vector Search
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
PINECONE_API_KEY=xxxxxxxxxxxxxxxxxx
PINECONE_INDEX_NAME=financial-reports-index

# Optional: Local Development
DEBUG=true
LOG_LEVEL=info
```

### Obtaining API Keys

- **Groq API**: Free tier (100k requests/month) at [console.groq.com](https://console.groq.com)
- **Pinecone**: Free tier (100k vectors) at [pinecone.io](https://pinecone.io)
- **PostgreSQL**: Use Docker (included in docker-compose.yml)
- **Redis**: Use Docker (included in docker-compose.yml)

---

## 🧪 Testing the Pipeline

### Test with Sample Financial PDF

1. Download a sample: Indian company quarterly results PDF (e.g., TCS, Infosys, Wipro)
2. Upload via UI or CLI:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/upload" \
     -F "file=@sample_financial.pdf"
   ```
3. Poll the status endpoint:
   ```bash
   curl "http://localhost:8000/api/v1/status/{document_id}"
   ```
4. Once `status: "COMPLETED"`, view results in the dashboard

### Test Earnings Call Chat

1. Upload a sample earnings call transcript
2. Try queries:
   - "What was mentioned about margin expansion?"
   - "Did they provide guidance for FY2027?"
   - "What were the risks discussed?"

---

## 📊 Performance & Limitations

### Current Capabilities
✅ Text-based PDFs (high accuracy)
✅ Tables with structured financial data
✅ LLM-powered metric extraction & summarization
✅ Multi-currency normalization (Lakh, Million, Thousand)
✅ Interactive visualizations for 60+ financial metrics
✅ RAG-based semantic search on earnings transcripts
✅ ML-based investment verdicts (Random Forest)

### Known Limitations
❌ Scanned PDFs (current model requires text-based PDFs)
❌ Unstructured financial narratives (works best with standard formats)
❌ Real-time data (processes historical documents)
❌ Non-English documents (optimized for English)

### Processing Time
- **Typical Financial PDF** (20-50 pages): 2-5 minutes
- **Earnings Call Transcript**: 1-2 minutes (including vector embedding)

---

## 🤝 Contributing

Contributions are welcome! Areas for enhancement:

1. **Scanned PDF Support**: Integrate advanced OCR models (Tesseract + ML-based layout analysis)
2. **Multi-Language Support**: Add language detection & translation
3. **Real-Time Data**: Connect to financial APIs (NSE, BSE) for live metrics
4. **Advanced ML**: Upgrade verdict model to ensemble methods (XGBoost, LightGBM)
5. **Mobile App**: React Native frontend for on-the-go analysis
6. **Competitor Analysis**: Multi-company financial comparisons

---

## 📝 License

This project is open source and available under the MIT License.

---

## 📧 Support

For questions, issues, or feature requests:
- Open a GitHub issue
- Contact: meetmodi45@example.com

---

## 🙏 Acknowledgments

- **FastAPI**: Modern, fast web framework for Python
- **Groq**: Incredibly fast LLM inference
- **Pinecone**: Managed vector database
- **LangChain**: LLM orchestration framework
- **React + Vite**: Blazing-fast frontend development
- **TailwindCSS**: Utility-first CSS framework
- **Recharts**: React charting library

---

**Built with ❤️ for retail investors | May 2026 - Jun 2026**
