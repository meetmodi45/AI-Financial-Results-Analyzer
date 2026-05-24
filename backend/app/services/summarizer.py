import os
import json
import re
from typing import Dict, Any, List
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

Generate an exhaustive extraction guide for this
earnings call transcript. This guide will be used to
score and filter sentences using TF-IDF, so every
list must be as comprehensive as possible.

Return this EXACT JSON structure — minimum 15 items
per list, maximum 30:

{{
  "core_metrics": [
    "Every key financial metric, ratio, and KPI that a buy-side analyst would track for a {SECTOR} company. Include full names AND common abbreviations. Think P&L metrics, balance sheet ratios, operational efficiency ratios, and segment-level KPIs."
  ],
  "causality_phrases": [
    "Phrases that signal WHY a result happened. Management uses these to explain causation. Include: driven by, due to, on account of, led by, owing to, as a result of, attributed to, primarily because, offset by, cushioned by, supported by, impacted by, hurt by, dragged by, aided by, boosted by, weighed down by, partly because, which was driven, stemming from, underpinned by, reflecting, consequent to"
  ],
  "guidance_phrases": [
    "Phrases that signal FUTURE commitments or management expectations. These sentences contain the investment thesis. Include: we expect, we guide, we target, we aspire to, going forward, by next quarter, we are confident of, our aspiration is, we will achieve, trajectory suggests, we anticipate, in the medium term, over the next few quarters, we remain committed, our guidance is, we reiterate, we are on track to, by end of fiscal, we project, our aim is, we plan to, we intend to"
  ],
  "risk_phrases": [
    "Phrases that signal headwinds, risks, or management acknowledging problems even without quoting a number. Include: headwind, pressure on, challenged by, we are watchful, risk remains, we are cautious, stress in, elevated, we are monitoring, uncertain, competitive intensity, we cannot rule out, remains a concern, softness in, moderation in, weak demand, muted, slowing, deterioration, we are watching closely, not out of the woods, continued pressure, structural challenge"
  ],
  "sector_specific_topics": [
    "Unique business topics, product lines, customer segments, regulatory items, and strategic themes specific to {SECTOR} that analysts always probe. Be exhaustive — think about every sub-segment, product type, regulatory ratio, channel, and geography that matters for {SECTOR} in India."
  ],
  "management_commitment_phrases": [
    "Phrases where management makes a specific commitment, defends a decision, or reiterates a position. High-signal even without numbers. Include: we are committed to, we will not compromise on, our stated goal is, we have guided for, we maintain our guidance, we reiterate, we are on track, unchanged from our earlier guidance, we have delivered on, we stand by, non-negotiable for us, our philosophy is, we will not participate in, firm commitment"
  ],
  "positive_signal_words": [
    "Words and short phrases that strongly indicate good news, improvement, or outperformance in a {SECTOR} context. Should include sector-specific terms for positive outcomes alongside generic terms like: recovery, improvement, uptick, normalizing, resilient, robust, ahead of guidance, strong traction, market share gain, expansion, accretion, stable, healthy, encouraging, improving trajectory, best ever, record, all-time high, sequential improvement, beat"
  ],
  "negative_signal_words": [
    "Words and short phrases that strongly indicate bad news, deterioration, or underperformance. Include sector-specific negative terms alongside generic: stress, elevated, deterioration, pressure, contraction, headwind, below expectation, slowdown, moderation, caution, miss, sequential decline, year-on-year decline, subdued, muted, weak, challenging environment, we were impacted, drag, adversely, shortfall"
  ],
  "numbers_context": [
    "Units, scales, and formats used in {SECTOR} financials so TF-IDF finds sentences with real data points. Include: basis points, bps, crore, INR, percent, percentage points, million, billion, X times, ratio, per quarter, annualized, run rate, sequential, YoY, QoQ, HoH, lakh crore, pb, per share, EPS, per unit, per store, per employee, absolute number, percentage, multiple"
  ],
  "irrelevant_content": [
    "Phrases that strongly indicate a sentence is procedural, boilerplate, or has zero financial signal. These sentences will be PENALIZED and removed. Include: thank you for the question, that is a great question, as I mentioned earlier, let me hand it over to, operator please go ahead, we will take the next question, ladies and gentlemen, you may now disconnect, for your information and records, safe harbour statement, pursuant to regulation, forward-looking statements, not been subjected to audit, good evening everyone, welcome to the earnings call, I will now hand over, with this I conclude, no further questions"
  ]
}}"""

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
  "Revenue grew 8% YoY to INR 4,200 Cr, driven by
   volume growth in the south India market and a 3%
   price increase taken in January; management guided
   this run rate to sustain in Q1 FY27"

Return this EXACT JSON structure:
{{
  "company":  "{COMPANY_NAME}",
  "quarter":  "{QUARTER} {FY}",
  "sector":   "{SECTOR}",

  "positive": [
    "Max 4 items. Each item must contain a specific number or metric AND the reason management gave. Focus on outperformance, margin expansion, growth acceleration, market share gains, successful new initiatives."
  ],
  "negative": [
    "Max 4 items. Each item must contain a specific number or metric AND the concern or reason. Focus on misses, elevated costs, stress in any segment, deteriorating ratios, competitive pressure management acknowledged."
  ],
  "guidance": [
    "Max 4 items. ONLY include explicit forward commitments. Must have a timeframe and a number or directional target. Do NOT include vague optimism like we are optimistic about growth. Only hard commitments with conditions."
  ],
  "key_risks_to_watch": [
    "Max 3 items. Risks management mentioned but did not fully resolve. Things that could invalidate the guidance if they worsen. Include the trigger condition."
  ]
}}

Rules:
- If management did not give a number for a point, do not include that point.
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
        # We use a cheap, fast model for Stage 1, and the main model for Stage 3
        # Llama 3 is great for strict JSON
        self.llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
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
        
        content = res.content.strip()
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
            logger.error(f"Failed to parse Stage 1 JSON: {e}\nContent: {content}")
            return {"irrelevant_content": ["thank you", "operator"]}

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
            logger.error(f"scikit-learn not available, falling back to first 40% of sentences: {e}")
            sentences_fallback = self._clean_text(transcript)
            return "\n".join(sentences_fallback[:max(1, int(len(sentences_fallback) * 0.4))])

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
            return "\n".join(sentences[:int(len(sentences)*0.4)])
            
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
        
        # Keep top 40%
        keep_count = max(1, int(len(sentences) * 0.40))
        top_sentences = final_scores[:keep_count]
        
        # Re-sort by original index to maintain chronological order
        top_sentences.sort(key=lambda x: x[1])
        
        filtered_transcript = "\n".join([s[2] for s in top_sentences])
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
        
        content = res.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        if content.startswith("```"):
            content = content[3:-3]
            
        try:
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to parse Stage 3 JSON: {e}\nContent: {content}")
            return {
                "positive": [],
                "negative": [],
                "guidance": [],
                "key_risks_to_watch": []
            }
