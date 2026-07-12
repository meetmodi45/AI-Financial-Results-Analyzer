import re
import logging
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Pattern to capture speaker prefixes like "Sanjiv Mehta (CEO):", "Operator:", "Q - Analyst Name:", etc.
SPEAKER_PATTERN = re.compile(r'^([A-Z0-9][A-Za-z0-9\s\-\.\(\)\/\&\,\’\']{1,45}):\s*(.*)$')

# Keywords that signal transition from Opening Remarks / Management Discussion to Q&A Session
QA_TRANSITION_PHRASES = [
    "begin the question-and-answer",
    "begin the question and answer",
    "open the floor for question",
    "begin the q&a",
    "begin the q and a",
    "question-and-answer session",
    "question & answer session",
    "q&a session",
    "first question",
    "questions and answers",
    "q & a session",
    "welcome to the question-and-answer"
]

class SpeakerTurn:
    """Represents a single continuous spoken segment in a transcript."""
    def __init__(self, speaker: str, text: str, page_num: int):
        self.speaker = speaker
        self.text = text
        self.page_num = page_num
        self.role = "Unknown"  # Classified later: Operator, Management, Analyst
        self.section = "Opening Remarks"  # Classified later: Opening Remarks, Management Discussion, Q&A

    def __repr__(self):
        return f"<SpeakerTurn speaker='{self.speaker}' role='{self.role}' section='{self.section}' page={self.page_num}>"

def is_speaker_line(line_text: str) -> Optional[tuple]:
    """Helper to detect speaker prefixes and split speaker from content."""
    m = SPEAKER_PATTERN.match(line_text)
    if not m:
        return None
    prefix = m.group(1).strip()
    rest = m.group(2).strip()
    
    # Exclude common non-speaker headings / page annotations
    prefix_lower = prefix.lower()
    excluded = {
        "note", "warning", "caution", "source", "date", "time", "venue", 
        "webcast", "participants", "page", "slide", "http", "https", 
        "disclaimer", "financials", "quarter", "fy", "year", "company",
        "earnings call", "transcript", "bse", "nse", "symbol"
    }
    if prefix_lower in excluded:
        return None
        
    # Punctuation check to prevent sentence fragments with colons from looking like speaker tags
    if any(c in prefix for c in ";!?@#$^*_+=\\|<>[]{}"):
        return None
        
    return prefix, rest

def parse_transcript(text_content: str, pages_list: Optional[List[Dict[str, Any]]] = None) -> List[SpeakerTurn]:
    """
    Parses transcript lines into a sequence of SpeakerTurn objects.
    Preserves page numbers if page-wise text is provided.
    """
    lines_with_page = []
    if pages_list:
        for p in pages_list:
            page_num = p.get("page_number", 1)
            page_text = p.get("text", "")
            for line in page_text.splitlines():
                lines_with_page.append((line, page_num))
    else:
        for line in text_content.splitlines():
            lines_with_page.append((line, 1))
            
    turns = []
    current_speaker = None
    current_text_lines = []
    current_page_num = 1
    
    for line_text, page_num in lines_with_page:
        line_clean = line_text.strip()
        if not line_clean:
            continue
            
        speaker_info = is_speaker_line(line_clean)
        if speaker_info:
            # Flush previous speaker's turn
            if current_speaker is not None:
                joined_text = " ".join(current_text_lines).strip()
                if joined_text:
                    turns.append(SpeakerTurn(current_speaker, joined_text, current_page_num))
            
            # Start new speaker turn
            current_speaker, remaining_text = speaker_info
            current_text_lines = [remaining_text] if remaining_text else []
            current_page_num = page_num
        else:
            # Continue current turn
            if current_speaker is not None:
                current_text_lines.append(line_clean)
            else:
                # Fallback for text appearing before any speaker tag
                current_speaker = "Operator"
                current_text_lines = [line_clean]
                current_page_num = page_num
                
    # Flush final turn
    if current_speaker is not None:
        joined_text = " ".join(current_text_lines).strip()
        if joined_text:
            turns.append(SpeakerTurn(current_speaker, joined_text, current_page_num))
            
    return turns

def classify_speaker_roles_and_sections(turns: List[SpeakerTurn]):
    """Classifies speaker roles and groups transcript sections chronologically."""
    current_section = "Opening Remarks"
    management_speakers = set()
    
    # Pass 1: Identify Operator, structural Management, and detect Q&A transitions
    for turn in turns:
        speaker_lower = turn.speaker.lower()
        
        # Identify Operator/Moderator
        if "operator" in speaker_lower or "moderator" in speaker_lower:
            turn.role = "Operator"
        else:
            # Check for explicit corporate management keywords
            is_mgmt_by_title = any(
                title in speaker_lower 
                for title in ["ceo", "cfo", "chairman", "director", "president", "vp", "executive", "manager", "md", "management"]
            )
            if is_mgmt_by_title:
                turn.role = "Management"
                management_speakers.add(turn.speaker)
        
        # Check for Q&A section starting
        text_lower = turn.text.lower()
        is_qa_transition = False
        
        if turn.role == "Operator":
            is_qa_transition = any(phrase in text_lower for phrase in QA_TRANSITION_PHRASES)
            
        if "q&a" in speaker_lower or "question" in speaker_lower:
            is_qa_transition = True
            
        if is_qa_transition and current_section != "Q&A":
            current_section = "Q&A"
            
        # If an executive or manager starts speaking during opening greetings, transition to Management Discussion
        if current_section == "Opening Remarks" and turn.role != "Operator":
            current_section = "Management Discussion"
            turn.role = "Management"
            management_speakers.add(turn.speaker)
            
        turn.section = current_section
        
    # Pass 2: Fill in remaining roles based on section context and discovered management speaker set
    for turn in turns:
        if turn.role == "Unknown":
            if turn.speaker in management_speakers:
                turn.role = "Management"
            elif turn.section == "Management Discussion":
                turn.role = "Management"
                management_speakers.add(turn.speaker)
            elif turn.section == "Opening Remarks":
                turn.role = "Operator"
            elif turn.section == "Q&A":
                # Speakers in Q&A who are not operator or management are analysts
                turn.role = "Analyst"
            else:
                turn.role = "Analyst"

def group_turns_into_logical_blocks(turns: List[SpeakerTurn]) -> List[List[SpeakerTurn]]:
    """Groups consecutive speaker turns into blocks representing presentations or Q&A exchanges."""
    blocks = []
    current_block = []
    current_section = None
    
    for turn in turns:
        # Flush current block if section type changes
        if turn.section != current_section:
            if current_block:
                blocks.append(current_block)
            current_block = [turn]
            current_section = turn.section
            continue
            
        if turn.section in ("Opening Remarks", "Management Discussion"):
            current_block.append(turn)
        else:
            # We are in Q&A: Group turns by analyst-executive exchanges.
            starts_new = False
            
            if turn.role == "Operator":
                text_lower = turn.text.lower()
                # Operator introducing the next question indicates a new Q&A sequence
                if any(p in text_lower for p in ["next question", "question from", "line of", "question is from"]):
                    starts_new = True
            elif turn.role == "Analyst":
                if not current_block:
                    starts_new = True
                else:
                    block_analysts = [t.speaker for t in current_block if t.role == "Analyst"]
                    # If this analyst is different from the analyst(s) in the current block, start a new block
                    if block_analysts and turn.speaker not in block_analysts:
                        starts_new = True
                            
            if starts_new:
                if current_block:
                    blocks.append(current_block)
                current_block = [turn]
            else:
                current_block.append(turn)
                
    if current_block:
        blocks.append(current_block)
        
    return blocks

def chunk_turns(turns_list: List[SpeakerTurn], max_size: int = 3000) -> List[Dict[str, Any]]:
    """
    Groups speaker turns into text chunks under max_size, maintaining speaker labels.
    If a turn is too large, it is split on sentence boundaries and continuation tags are added.
    """
    if not turns_list:
        return []
        
    def format_turns(t_list):
        return "\n\n".join(f"{t.speaker}:\n{t.text}" for t in t_list)
        
    full_text = format_turns(turns_list)
    if len(full_text) <= max_size:
        return [{
            "text": full_text,
            "speakers": list(set(t.speaker for t in turns_list)),
            "start_page": turns_list[0].page_num,
            "end_page": turns_list[-1].page_num
        }]
        
    chunks = []
    current_group = []
    current_len = 0
    
    for turn in turns_list:
        turn_text = f"{turn.speaker}:\n{turn.text}"
        turn_len = len(turn_text) + 2
        
        if turn_len > max_size:
            # Flush current group
            if current_group:
                chunks.append({
                    "text": format_turns(current_group),
                    "speakers": list(set(t.speaker for t in current_group)),
                    "start_page": current_group[0].page_num,
                    "end_page": current_group[-1].page_num
                })
                current_group = []
                current_len = 0
                
            # Split large turn on sentence boundaries
            sentences = re.split(r'(?<=[.!?])\s+', turn.text)
            current_sentences = []
            current_sent_len = 0
            
            speaker_header = f"{turn.speaker} (continued):\n"
            header_len = len(speaker_header)
            
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                    
                sent_len = len(sent) + 1
                if current_sent_len + sent_len + header_len > max_size:
                    if current_sentences:
                        text_content = f"{turn.speaker}:\n" + " ".join(current_sentences) if not chunks else speaker_header + " ".join(current_sentences)
                        chunks.append({
                            "text": text_content,
                            "speakers": [turn.speaker],
                            "start_page": turn.page_num,
                            "end_page": turn.page_num
                        })
                        current_sentences = [sent]
                        current_sent_len = sent_len
                    else:
                        # Fallback for single sentence exceeding max_size
                        text_content = f"{turn.speaker}:\n" + sent
                        chunks.append({
                            "text": text_content,
                            "speakers": [turn.speaker],
                            "start_page": turn.page_num,
                            "end_page": turn.page_num
                        })
                        current_sentences = []
                        current_sent_len = 0
                else:
                    current_sentences.append(sent)
                    current_sent_len += sent_len
                    
            if current_sentences:
                text_content = f"{turn.speaker}:\n" + " ".join(current_sentences) if not chunks else speaker_header + " ".join(current_sentences)
                chunks.append({
                    "text": text_content,
                    "speakers": [turn.speaker],
                    "start_page": turn.page_num,
                    "end_page": turn.page_num
                })
        else:
            if current_len + turn_len > max_size:
                if current_group:
                    chunks.append({
                        "text": format_turns(current_group),
                        "speakers": list(set(t.speaker for t in current_group)),
                        "start_page": current_group[0].page_num,
                        "end_page": current_group[-1].page_num
                    })
                current_group = [turn]
                current_len = turn_len
            else:
                current_group.append(turn)
                current_len += turn_len
                
    if current_group:
        chunks.append({
            "text": format_turns(current_group),
            "speakers": list(set(t.speaker for t in current_group)),
            "start_page": current_group[0].page_num,
            "end_page": current_group[-1].page_num
        })
        
    return chunks

def create_structured_chunks(text_content: str, document_id: str, company_name: str, filename: str, pages_list: Optional[List[Dict[str, Any]]] = None) -> List[Document]:
    """
    Parses a transcript and generates structure-aware chunk documents with enriched metadata.
    """
    turns = parse_transcript(text_content, pages_list)
    classify_speaker_roles_and_sections(turns)
    blocks = group_turns_into_logical_blocks(turns)
    
    all_chunks_info = []
    question_count = 0
    
    for block in blocks:
        if not block:
            continue
        section_type = block[0].section
        is_qa = (section_type == "Q&A")
        
        question_number = None
        if is_qa:
            has_analyst = any(t.role == "Analyst" for t in block)
            if has_analyst:
                question_count += 1
                question_number = question_count
                
        block_chunks = chunk_turns(block, max_size=3000)
        for bc in block_chunks:
            bc["section_type"] = section_type
            bc["question_number"] = question_number
            all_chunks_info.append(bc)
            
    total_chunks = len(all_chunks_info)
    documents = []
    
    for i, info in enumerate(all_chunks_info):
        metadata = {
            "document_id": document_id,
            "company_name": company_name,
            "content_type": "concall_transcript",
            "chunk_id": f"{document_id}_chunk_{i}",
            "chunk_index": i,
            "section_type": info["section_type"],
            "speakers": info["speakers"],
            "speakers_involved": ", ".join(sorted(info["speakers"])),
            "source_filename": filename,
            "page_number": info["start_page"],
            "page_range": f"{info['start_page']}-{info['end_page']}" if info['start_page'] != info['end_page'] else f"{info['start_page']}",
            "total_chunks": total_chunks
        }
        if info["question_number"] is not None:
            metadata["question_number"] = info["question_number"]
            
        doc = Document(
            page_content=info["text"],
            metadata=metadata
        )
        documents.append(doc)
        
    return documents

def retrieve_with_neighbors(vectorstore, query: str, document_id: str, k: int = 5) -> List[Document]:
    """
    Retrieve similarity matching chunks for the query, and include the immediately previous
    and immediately next chunks for each retrieved chunk (if they exist).
    Deduplicates results and maintains the original chronological ordering.
    """
    # 1. Similarity search to find top matching chunks
    retrieved_docs = vectorstore.similarity_search(
        query,
        k=k,
        filter={"document_id": document_id}
    )
    
    if not retrieved_docs:
        return []
        
    target_indices = set()
    total_chunks = None
    
    # 2. Extract indices of matches
    for doc in retrieved_docs:
        chunk_index = doc.metadata.get("chunk_index")
        if chunk_index is not None:
            try:
                idx = int(chunk_index)
                target_indices.add(idx)
                if "total_chunks" in doc.metadata:
                    total_chunks = int(doc.metadata["total_chunks"])
            except (ValueError, TypeError):
                pass
                
    # 3. Add neighboring indices
    all_indices = set()
    for idx in target_indices:
        all_indices.add(idx)
        if idx > 0:
            all_indices.add(idx - 1)
        if total_chunks is not None:
            if idx < total_chunks - 1:
                all_indices.add(idx + 1)
        else:
            # If total_chunks is not available in metadata, try to fetch idx + 1 anyway
            all_indices.add(idx + 1)
            
    # Sort to maintain chronological ordering of the transcript
    sorted_indices = sorted(list(all_indices))
    
    # 4. Fetch the neighbor vectors from Pinecone in a single batch lookup
    ids_to_fetch = [f"{document_id}_chunk_{idx}" for idx in sorted_indices]
    index = vectorstore._index
    
    try:
        fetch_response = index.fetch(ids=ids_to_fetch, namespace=document_id)
        
        # Safely parse Pinecone response across SDK versions
        vectors = {}
        if hasattr(fetch_response, "vectors"):
            vectors = fetch_response.vectors
        elif isinstance(fetch_response, dict):
            vectors = fetch_response.get("vectors", {})
        else:
            vectors = getattr(fetch_response, "vectors", {})
            
        fetched_docs = []
        for idx in sorted_indices:
            v_id = f"{document_id}_chunk_{idx}"
            if v_id in vectors:
                v_data = vectors[v_id]
                metadata_dict = {}
                if hasattr(v_data, "metadata"):
                    metadata_dict = v_data.metadata
                elif isinstance(v_data, dict):
                    metadata_dict = v_data.get("metadata", {})
                else:
                    metadata_dict = getattr(v_data, "metadata", {})
                    
                if not isinstance(metadata_dict, dict):
                    metadata_dict = dict(metadata_dict)
                    
                page_content = metadata_dict.get("text", "")
                cleaned_metadata = {k: v for k, v in metadata_dict.items() if k != "text"}
                
                fetched_docs.append(Document(
                    page_content=page_content,
                    metadata=cleaned_metadata
                ))
                
        if fetched_docs:
            return fetched_docs
            
    except Exception as e:
        logger.error(f"Error fetching neighbor chunks from Pinecone: {e}", exc_info=True)
        
    # Backward compatibility fallback: sort matching retrieved docs by index
    logger.warning("Falling back to retrieved documents sorted by chunk index.")
    retrieved_docs.sort(key=lambda x: int(x.metadata.get("chunk_index", 0)))
    return retrieved_docs

