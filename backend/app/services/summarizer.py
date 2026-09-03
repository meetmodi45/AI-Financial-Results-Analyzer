import os
import json
import re
from typing import Dict, Any, List
from app.core.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import logging

logger = logging.getLogger(__name__)

STAGE_1_SYSTEM = """You are a senior equity research analyst with 20+ years
of experience covering {SECTOR} companies in India.
Return ONLY valid JSON. No explanation, no markdown,
no preamble. The output will be parsed by a script."""

STAGE_1_USER = """Company  : {COMPANY_NAME}
Sector   : {SECTOR}
Quarter  : {QUARTER} {FY}

Generate a concise extraction guide for this
earnings call transcript. This guide will be used to
score and filter sentences using TF-IDF.

Return this EXACT JSON structure — minimum 5 items per list, maximum 10 (keep each item short):

{{
  "core_metrics": [
    "Key financial metrics and KPIs for a {SECTOR} company (max 10 items)."
  ],
  "causality_phrases": [
    "Phrases signaling why results happened (e.g. driven by, due to, led by)."
  ],
  "guidance_phrases": [
    "Phrases signaling future commitments or management expectations."
  ],
  "risk_phrases": [
    "Phrases signaling headwinds, risks, or concerns."
  ],
  "sector_specific_topics": [
    "Unique business topics or product lines specific to {SECTOR} (max 10 short items)."
  ],
  "management_commitment_phrases": [
    "Phrases where management makes a specific commitment."
  ],
  "positive_signal_words": [
    "Words and short phrases indicating good news or growth."
  ],
  "negative_signal_words": [
    "Words and short phrases indicating bad news or margin pressure."
  ],
  "numbers_context": [
    "Units and scales used in {SECTOR} financials (crore, INR, %, bps, YoY, QoQ)."
  ],
  "irrelevant_content": [
    "Procedural boilerplate phrases to ignore (thank you for question, operator please)."
  ]
}}"""

DEFAULT_DOMAIN_GUIDE = {
    "core_metrics": ["Revenue", "EBITDA", "Net Profit", "PAT", "EPS", "Margin", "YoY Growth", "QoQ Growth", "Volume", "Realization", "CapEx", "Debt", "Free Cash Flow"],
    "causality_phrases": ["driven by", "due to", "on account of", "led by", "owing to", "as a result of", "attributed to", "primarily because", "offset by", "supported by", "impacted by", "boosted by", "weighed down by"],
    "guidance_phrases": ["we expect", "we guide", "we target", "going forward", "by next quarter", "we are confident of", "we anticipate", "over the next few quarters", "we remain committed", "our guidance is", "we project", "we plan to"],
    "risk_phrases": ["headwind", "pressure on", "challenged by", "risk remains", "we are cautious", "stress in", "elevated", "uncertain", "competitive intensity", "softness in", "weak demand", "muted", "slowing", "deterioration"],
    "sector_specific_topics": ["market share", "capacity expansion", "order book", "client addition", "raw material cost", "pricing power", "channel inventory", "regulatory compliance", "product mix", "exports"],
    "management_commitment_phrases": ["we are committed to", "our stated goal is", "we have guided for", "we maintain our guidance", "we reiterate", "we are on track"],
    "positive_signal_words": ["recovery", "improvement", "uptick", "normalizing", "resilient", "robust", "ahead of guidance", "strong traction", "market share gain", "expansion", "growth", "record"],
    "negative_signal_words": ["stress", "elevated", "deterioration", "pressure", "contraction", "headwind", "below expectation", "slowdown", "moderation", "caution", "miss", "decline", "drag"],
    "numbers_context": ["basis points", "bps", "crore", "INR", "percent", "million", "billion", "ratio", "per quarter", "YoY", "QoQ", "per share", "EPS"],
    "irrelevant_content": ["thank you for the question", "operator please go ahead", "safe harbour statement", "ladies and gentlemen", "good evening everyone", "welcome to the earnings call", "I will now hand over"]
}

STAGE_3_SYSTEM = """You are a senior equity research analyst writing a
concise brief for a fund manager who has 3 minutes
to read it before a trading decision.
Return ONLY valid JSON. No markdown. No explanation.
No text before or after the JSON object."""

STAGE_3_USER = """Company : {COMPANY_NAME}
Sector  : {SECTOR}
Quarter : {QUARTER} {FY}

Read the earnings call transcript below carefully.

Your job is to extract ONLY factual statements that
management made. Do not infer. Do not extrapolate.
Only include what management explicitly said.

For every point you extract you MUST include:
  1. The fact       — what actually happened (with number)
  2. The reason     — why management said it happened
  3. The direction  — is it improving or worsening

For guidance points you MUST include:
  1. The commitment — exactly what management guided
  2. The timeframe  — by when (quarter, half year, FY)
  3. The condition  — what needs to happen for it to hold

BAD example (do not do this):
  "Revenue grew 8%"

GOOD example (do this):
  "Rev +8% YoY to INR 4.2k Cr driven by South India vol & 3% Jan price hike; guided to sustain in Q1 FY27"

Return this EXACT JSON structure:
{{
  "company":  "{COMPANY_NAME}",
  "quarter":  "{QUARTER} {FY}",
  "sector":   "{SECTOR}",

  "key_takeaways": [
    "Exactly 3 high-impact executive summary bullet points that capture the absolute most critical strategic and financial takeaways of the call. This is what a fund manager must read first."
  ],
  "positive": [
    "Max 5 items. Each item must contain a specific metric OR a critical strategic insight AND the reason management gave. Focus on outperformance, margin expansion, growth acceleration, market share gains, successful new initiatives."
  ],
  "negative": [
    "Max 5 items. Each item must contain a specific metric OR a critical strategic insight AND the concern or reason. Focus on misses, elevated costs, stress in any segment, deteriorating ratios, competitive pressure management acknowledged."
  ],
  "guidance": [
    "Max 4 items. ONLY include explicit forward commitments. Must have a timeframe and a number or directional target. Do NOT include vague optimism like we are optimistic about growth. Only hard commitments with conditions."
  ],
  "key_risks_to_watch": [
    "Max 4 items. Risks management mentioned but did not fully resolve. Things that could invalidate the guidance if they worsen. Include the trigger condition."
  ],
  "capital_allocation": [
    "Max 3 items. Specific details on CapEx, debt repayment, dividend payouts, share buybacks, or M&A activities."
  ],
  "strategic_initiatives": [
    "Max 4 items. Important macro commentary, demand environment updates, pricing leverage, new product pipelines, or Q&A pushback themes."
  ],
  "suggested_questions": [
    "Exactly 3 highly-specific, insightful questions (each 10-15 words) that an investor or analyst would want to ask the chatbot about this specific call, based on the key issues, risks, or segment performance discussed. Make them concrete, contextual, and unique to this company and quarter."
  ]
}}

Rules:
- Be concise (around 20-30 words per point). Use abbreviations (e.g., Rev, Vol, Mgmt, YoY) to save space and remove filler words, but ALWAYS preserve the context and the 'why' (the reason/driver behind the metric).
- If management gave a number for a point, include it. Otherwise, include the point if it is a critical strategic insight.
- Preserve the causality — never separate a result from its reason in the same point.
- Guidance must have a timeframe or it is not guidance.
- key_risks_to_watch is for open-ended concerns only.
- Do not fabricate any number not present in the text.
- Do not summarize what analysts said, only management.

Transcript (pre-filtered, high-signal sentences only):
{FILTERED_TRANSCRIPT}"""

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
try:
    os.makedirs(CACHE_DIR, exist_ok=True)
except OSError as e:
    logger.warning(f"Could not create cache directory {CACHE_DIR}: {e}. Sector guides will not be cached to disk.")

class ConcallSummarizer:
    def __init__(self):
        fallback_llm = ChatGroq(model=settings.GROQ_MODEL, temperature=0, api_key=settings.GROQ_API_KEY)
        api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        if api_key:
            try:
                primary_llm = ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    temperature=0,
                    api_key=api_key
                )
                self.llm = primary_llm.with_fallbacks([fallback_llm])
            except Exception as e:
                logger.warning(f"Failed to initialize ChatGoogleGenerativeAI, falling back to Groq: {e}")
                self.llm = fallback_llm
        else:
            self.llm = fallback_llm
        self._vectorizer = None  # Lazily initialized to avoid import-time sklearn crash

    def _get_cache_path(self, sector: str) -> str:
        s_safe = "".join(c if c.isalnum() else "_" for c in sector).lower()
        return os.path.join(CACHE_DIR, f"{s_safe}_guide.json")

    def stage_1_get_domain_guide(self, company_name: str, sector: str, quarter: str, fy: str) -> Dict[str, List[str]]:
        if not sector or sector == "Unknown":
            sector = "General Corporate"

        cache_path = self._get_cache_path(sector)
        if os.path.exists(cache_path):
            logger.info(f"Using cached domain guide for sector: {sector}")
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        
        logger.info(f"Generating domain guide for sector: {sector}")
        prompt = ChatPromptTemplate.from_messages([
            ("system", STAGE_1_SYSTEM),
            ("human", STAGE_1_USER)
        ])
        
        chain = prompt | self.llm
        res = chain.invoke({
            "SECTOR": sector,
            "COMPANY_NAME": company_name,
            "QUARTER": quarter,
            "FY": fy
        })
        
        raw_content = res.content
        if isinstance(raw_content, list):
            content = " ".join([b.get("text", "") for b in raw_content if isinstance(b, dict) and "text" in b])
        else:
            content = str(raw_content)
            
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        if content.startswith("```"):
            content = content[3:-3]
            
        try:
            guide = json.loads(content)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(guide, f, indent=2)
            return guide
        except Exception as e:
            logger.error(f"Failed to parse Stage 1 JSON: {e}. Falling back to default domain guide.")
            return DEFAULT_DOMAIN_GUIDE

    def _clean_text(self, text: str) -> List[str]:
        # Strip legal headers, moderator lines, compress speaker names, remove page markers
        lines = text.split('\n')
        cleaned_sentences = []
        current_sentence = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Basic heuristics
            if line.lower().startswith("operator:") or line.lower().startswith("q -"):
                continue
            if re.match(r'^page \d+', line, re.IGNORECASE):
                continue
                
            # Split by basic sentence terminators
            sentences = re.split(r'(?<=[.!?])\s+', line)
            for s in sentences:
                s = s.strip()
                if len(s.split()) > 3:  # Only keep reasonable length sentences
                    cleaned_sentences.append(s)
                    
        return cleaned_sentences

    def stage_2_tfidf_filter(self, transcript: str, guide: Dict[str, List[str]]) -> str:
        # Lazy import sklearn here so a missing/broken install doesn't crash the module at startup
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError as e:
            logger.error(f"scikit-learn not available, falling back to first 80% of sentences: {e}")
            sentences_fallback = self._clean_text(transcript)
            return "\n".join(sentences_fallback[:max(1, int(len(sentences_fallback) * 0.8))])

        if self._vectorizer is None:
            self._vectorizer = TfidfVectorizer(ngram_range=(1, 3), stop_words='english')

        sentences = self._clean_text(transcript)
        if not sentences:
            return ""
            
        # Combine all positive signals into one document
        positive_signal_docs = []
        for key in guide:
            if key != "irrelevant_content":
                positive_signal_docs.extend(guide[key])
        positive_corpus = " ".join(positive_signal_docs)
        
        negative_corpus = " ".join(guide.get("irrelevant_content", []))
        
        # We need to compute cosine similarity.
        # Create a corpus where the first doc is positive, second is negative, and rest are sentences.
        corpus = [positive_corpus, negative_corpus] + sentences
        
        try:
            X = self._vectorizer.fit_transform(corpus)
        except ValueError:
            return "\n".join(sentences[:int(len(sentences)*0.8)])
            
        # X[0] is positive_corpus vector, X[1] is negative_corpus vector
        # X[2:] are the sentences
        pos_vec = X[0:1]
        neg_vec = X[1:2]
        sent_vecs = X[2:]

        # cosine_similarity imported above in this scope
        
        pos_scores = cosine_similarity(sent_vecs, pos_vec).flatten()
        neg_scores = cosine_similarity(sent_vecs, neg_vec).flatten()
        
        final_scores = []
        for i in range(len(sentences)):
            score = pos_scores[i] - (neg_scores[i] * 1.5)
            final_scores.append((score, i, sentences[i]))
            
        # Sort by score descending
        final_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Select top TF-IDF scored sentences up to MAX_CHARS safety limit (12,000 chars ≈ 3,000 tokens)
        # This strictly prevents Groq 413 rate limit errors (6,000 TPM limit on free tier)
        selected_sentences = []
        char_count = 0
        MAX_CHARS = 12000
        
        for score, idx, sentence in final_scores:
            if char_count + len(sentence) > MAX_CHARS:
                break
            selected_sentences.append((idx, sentence))
            char_count += len(sentence)
            
        # Re-sort by original index to maintain chronological narrative order
        selected_sentences.sort(key=lambda x: x[0])
        
        filtered_transcript = "\n".join([s[1] for s in selected_sentences])
        return filtered_transcript

    def stage_3_summarize(self, company_name: str, sector: str, quarter: str, fy: str, filtered_transcript: str) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_messages([
            ("system", STAGE_3_SYSTEM),
            ("human", STAGE_3_USER)
        ])
        
        chain = prompt | self.llm
        res = chain.invoke({
            "COMPANY_NAME": company_name,
            "SECTOR": sector,
            "QUARTER": quarter,
            "FY": fy,
            "FILTERED_TRANSCRIPT": filtered_transcript
        })
        
        raw_content = res.content
        if isinstance(raw_content, list):
            content = " ".join([b.get("text", "") for b in raw_content if isinstance(b, dict) and "text" in b])
        else:
            content = str(raw_content)
            
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        if content.startswith("```"):
            content = content[3:-3]
            
        try:
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to parse Stage 3 JSON: {e}\nContent: {content}")
            return {
                "key_takeaways": [],
                "positive": [],
                "negative": [],
                "guidance": [],
                "key_risks_to_watch": [],
                "capital_allocation": [],
                "strategic_initiatives": []
            }
