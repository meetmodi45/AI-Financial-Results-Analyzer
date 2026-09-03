import os
import sys
from dotenv import load_dotenv
load_dotenv('../.env')

sys.path.append(os.path.abspath('..'))
from app.agents.agent_8_llm_summary import process_llm_summary
from app.core.db import SessionLocal
from app.models.document import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings

db = SessionLocal()
doc = db.query(Document).filter(Document.analysis_results != None).first()
if doc:
    res_dict = doc.analysis_results or {}
    context_payload = (
        f"--- CALCULATED METRICS ---\n"
        f"QoQ Revenue Growth: {res_dict.get('qoq_growth')}% \n"
        f"YoY Revenue Growth: {res_dict.get('yoy_growth')}% \n"
        f"QoQ EPS Growth: {res_dict.get('eps_qoq')}% \n"
        f"YoY EPS Growth: {res_dict.get('eps_yoy')}% \n"
        f"Net Profit Margin: {res_dict.get('net_margin')}%\n"
        f"EBITDA Margin: {res_dict.get('ebitda_margin')}%\n"
    )
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        temperature=0.0,
        max_output_tokens=1000,
        google_api_key=settings.GEMINI_API_KEY,
        model_kwargs={'response_mime_type': 'application/json'}
    )
    prompt = ChatPromptTemplate.from_messages([
        ('system', 'You are a Senior Institutional Financial Analyst.\nSynthesize a clean, highly organized, and non-repetitive analyst summary based on the provided metrics.\nSTRICT RULES:\n1. Output ONLY a single JSON object with key "executive_summary" containing a list of 4-6 distinct, high-value bullet point strings.\n2. DO NOT repeat the same metric or stat across multiple bullet points. Mention each metric (e.g., revenue growth, EPS, net margin) AT MOST ONCE.\n3. Structure the points logically in sequence:\n   - Point 1: Revenue & Top-line Performance (QoQ / YoY)\n   - Point 2: Earnings & EPS Strength\n   - Point 3: Profitability & Operational Margins (Net Margin / EBITDA)\n   - Point 4: Key Growth Driver or Strategic Conclusion\n   - Point 5: Key Risk or Area of Caution\n4. Write apostrophes as standard unescaped characters \' inside double-quoted JSON strings (e.g. write "company\'s", NOT "company\\\'s").'),
        ('human', 'Analyze this financial data and output a single valid JSON object:\n\n{text}')
    ])
    chain = prompt | llm
    raw_response = chain.invoke({'text': context_payload})
    print('RAW CONTENT TYPE:', type(raw_response.content))
    print('RAW CONTENT:', repr(raw_response.content))
