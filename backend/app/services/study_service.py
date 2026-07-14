import re
import json
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.models import Document, DocumentChunk, DocumentSummary, Quiz, QuizQuestion, FlashcardSet, Flashcard
from app.services.llm_service import llm_service

class StudyService:
    def _detect_chapters(self, chunks: List[DocumentChunk]) -> List[Dict[str, Any]]:
        """
        Groups document chunks into chapters.
        Uses regex heuristics for chapter titles, falling back to equal size grouping.
        """
        # Sort chunks by page number and ID
        sorted_chunks = sorted(chunks, key=lambda c: (c.page_number, c.id))
        if not sorted_chunks:
            return []

        chapters = []
        chapter_pattern = re.compile(
            r'^\s*(Chapter|Section|Unit|Part|Ch\.)\s+(\d+|[IVXLCDM]+)\b', 
            re.IGNORECASE
        )
        whitelist_pattern = re.compile(
            r'^\s*(Introduction|Conclusion|Abstract|References|Summary|Appendix|Table\s+of\s+Contents|Index|Bibliography|Preface|Acknowledgment|Discussion|Results|Methodology|Literature\s+Review|Background)\b',
            re.IGNORECASE
        )
        
        current_chapter_chunks = []
        current_title = "Introduction"
        start_page = sorted_chunks[0].page_number
        
        for chunk in sorted_chunks:
            # Check the first 2 lines of the chunk for a chapter heading
            lines = [line.strip() for line in chunk.text.split('\n') if line.strip()][:2]
            found_heading = False
            
            for line in lines:
                match = chapter_pattern.match(line)
                whitelist_match = whitelist_pattern.match(line)
                if match or (whitelist_match and len(line) < 40 and not line.endswith('.')):
                    # We found a potential chapter boundary!
                    if current_chapter_chunks:
                        chapters.append({
                            "title": current_title,
                            "chunks": current_chapter_chunks,
                            "start_page": start_page,
                            "end_page": current_chapter_chunks[-1].page_number
                        })
                    current_chapter_chunks = [chunk]
                    current_title = line
                    start_page = chunk.page_number
                    found_heading = True
                    break
            
            if not found_heading:
                current_chapter_chunks.append(chunk)
                
        # Append the final chapter
        if current_chapter_chunks:
            chapters.append({
                "title": current_title,
                "chunks": current_chapter_chunks,
                "start_page": start_page,
                "end_page": current_chapter_chunks[-1].page_number
            })
            
        # Fallback: if only 1 chapter was detected, split the chunks into at most 3 logical parts
        if len(chapters) <= 1 and len(sorted_chunks) > 5:
            chapters = []
            group_size = max(5, len(sorted_chunks) // 3 + 1)
            chunk_groups = [sorted_chunks[i:i + group_size] for i in range(0, len(sorted_chunks), group_size)]
            for i, group in enumerate(chunk_groups):
                chapters.append({
                    "title": f"Part {i + 1}",
                    "chunks": group,
                    "start_page": group[0].page_number,
                    "end_page": group[-1].page_number
                })
                
        return chapters

    async def generate_document_summary(self, document_id: int, db: Session) -> DocumentSummary:
        """
        Generate and persist the summary, key points, conclusions, and chapter summaries.
        """
        # Check if already exists
        existing = db.query(DocumentSummary).filter(DocumentSummary.document_id == document_id).first()
        if existing:
            return existing
            
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
        if not chunks:
            raise ValueError("Document contains no chunks to summarize.")
            
        # 1. Group chunks into chapters
        detected_chapters = self._detect_chapters(chunks)
        chapters_data = []
        
        # 2. Summarize each chapter
        for chapter in detected_chapters:
            # Semantic skimming: if the chapter has many chunks, take the first 2 sentences of each chunk
            # to cover the entire text range without overloading CPU context window.
            if len(chapter["chunks"]) > 3:
                skimming_lines = []
                for c in chapter["chunks"]:
                    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', c.text) if s.strip()]
                    if sentences:
                        skimming_lines.append(sentences[0])
                        if len(sentences) > 1 and len(c.text) > 800:
                            skimming_lines.append(sentences[1])
                chapter_text = " ".join(skimming_lines)[:3000]
            else:
                chapter_text = " ".join([c.text for c in chapter["chunks"]])[:3000]
            
            system_prompt = (
                "You are an academic summarizer. Read the text segment and provide: "
                "1. A short title (less than 8 words) describing the segment. "
                "2. A concise 2-3 sentence summary of its key points.\n"
                "Respond in this exact format:\n"
                "Title: [Your generated title]\n"
                "Summary: [Your summary]"
            )
            
            prompt = f"Summarize the following text:\n\n{chapter_text}"
            response = await llm_service.generate_response(prompt=prompt, system_prompt=system_prompt, temperature=0.3)
            
            # Parse title and summary
            title = chapter["title"]
            summary = "No summary generated."
            
            title_match = re.search(r'Title:\s*(.*)', response, re.IGNORECASE)
            summary_match = re.search(r'Summary:\s*(.*)', response, re.DOTALL | re.IGNORECASE)
            
            if title_match:
                title = title_match.group(1).strip()
            if summary_match:
                summary = summary_match.group(1).strip()
            else:
                # Fallback if parsing failed
                summary = response.replace("Title:", "").replace("Summary:", "").strip()
                
            chapters_data.append({
                "title": title,
                "summary": summary,
                "start_page": chapter["start_page"],
                "end_page": chapter["end_page"]
            })
            
        # 3. Combine summaries to create full document summary, key points, and conclusions
        combined_chapters_context = "\n\n".join([
            f"Chapter: {ch['title']}\nSummary: {ch['summary']}"
            for ch in chapters_data
        ])
        
        system_prompt = (
            "You are an expert academic tutor. Analyze the provided chapter summaries of a document and generate:\n"
            "1. A comprehensive document summary (2-3 paragraphs).\n"
            "2. A list of 4-6 key concepts/points.\n"
            "3. A concise conclusion summarizing the final takeaways.\n"
            "You MUST respond in this exact format with the tags:\n"
            "[SUMMARY]\n"
            "(Your summary text)\n"
            "[KEY_POINTS]\n"
            "- Point 1\n"
            "- Point 2\n"
            "[CONCLUSIONS]\n"
            "(Your conclusions text)"
        )
        
        prompt = f"Document Chapter Summaries:\n\n{combined_chapters_context}"
        response = await llm_service.generate_response(prompt=prompt, system_prompt=system_prompt, temperature=0.3)
        
        # Parse output tags
        full_summary = "Summary generation failed."
        key_points_list = []
        conclusions = "Conclusion generation failed."
        
        summary_block = re.search(r'\[SUMMARY\]\s*(.*?)\s*(?=\[KEY_POINTS\]|$)', response, re.DOTALL | re.IGNORECASE)
        points_block = re.search(r'\[KEY_POINTS\]\s*(.*?)\s*(?=\[CONCLUSIONS\]|$)', response, re.DOTALL | re.IGNORECASE)
        conclusion_block = re.search(r'\[CONCLUSIONS\]\s*(.*)', response, re.DOTALL | re.IGNORECASE)
        
        if summary_block:
            full_summary = summary_block.group(1).strip()
        if conclusion_block:
            conclusions = conclusion_block.group(1).strip()
            
        if points_block:
            points_text = points_block.group(1).strip()
            key_points_list = [
                line.strip('-* ').strip()
                for line in points_text.split('\n')
                if line.strip()
            ]
        else:
            # Fallback points extraction
            key_points_list = ["Review the chapter summaries to extract key points."]
            
        # 4. Save to Database
        db_summary = DocumentSummary(
            document_id=document_id,
            summary_text=full_summary,
            key_points=json.dumps(key_points_list),
            conclusions=conclusions,
            chapters=json.dumps(chapters_data)
        )
        
        db.add(db_summary)
        db.commit()
        db.refresh(db_summary)
        
        return db_summary

    async def generate_quiz(self, document_id: int, user_id: int, db: Session) -> Quiz:
        """
        Generates and persists an interactive quiz containing MCQ, T/F, and Short Answer questions.
        """
        # Fetch the document summary to base the questions on
        summary_record = db.query(DocumentSummary).filter(DocumentSummary.document_id == document_id).first()
        if not summary_record:
            summary_record = await self.generate_document_summary(document_id, db)
            
        summary_context = summary_record.summary_text + "\nKey Points:\n" + summary_record.key_points
        
        system_prompt = (
            "You are an academic examiner. Design a 9-question study quiz based strictly on the provided summary text.\n"
            "The quiz must contain precisely:\n"
            "- 3 Multiple Choice Questions (MCQ)\n"
            "- 3 True/False Questions (TF)\n"
            "- 3 Short Answer Questions (SHORT) (questions requiring a 1-3 word factual answer)\n\n"
            "Format the response using these EXACT tags so they can be parsed by regex:\n"
            "[MCQ_START]\n"
            "Q: (Question text)\n"
            "A) (Option A)\n"
            "B) (Option B)\n"
            "C) (Option C)\n"
            "D) (Option D)\n"
            "Correct: (A/B/C/D)\n"
            "Explanation: (Why it is correct)\n"
            "[MCQ_END]\n\n"
            "[TF_START]\n"
            "Q: (Question text)\n"
            "Correct: (True/False)\n"
            "Explanation: (Why it is correct)\n"
            "[TF_END]\n\n"
            "[SHORT_START]\n"
            "Q: (Question text)\n"
            "Correct: (Concise answer keyword)\n"
            "Explanation: (Short explanation)\n"
            "[SHORT_END]\n"
        )
        
        prompt = f"Document Summary:\n\n{summary_context}"
        response = await llm_service.generate_response(prompt=prompt, system_prompt=system_prompt, temperature=0.7)
        
        # Parse questions (strict regex)
        mcq_blocks = re.findall(r'\[MCQ_START\](.*?)\[MCQ_END\]', response, re.DOTALL | re.IGNORECASE)
        tf_blocks = re.findall(r'\[TF_START\](.*?)\[TF_END\]', response, re.DOTALL | re.IGNORECASE)
        short_blocks = re.findall(r'\[SHORT_START\](.*?)\[SHORT_END\]', response, re.DOTALL | re.IGNORECASE)
        
        # Tolerant block scanner if strict tags are missing
        if not mcq_blocks and not tf_blocks and not short_blocks:
            blocks = [b.strip() for b in response.split('\n\n') if b.strip()]
            for b in blocks:
                b_lower = b.lower()
                if "a)" in b_lower or "b)" in b_lower:
                    mcq_blocks.append(b)
                elif "true/false" in b_lower or "t/f" in b_lower or "correct: true" in b_lower or "correct: false" in b_lower:
                    tf_blocks.append(b)
                elif "q:" in b_lower or "question:" in b_lower:
                    short_blocks.append(b)

        # Grounded rule-based quiz generation fallback using summary key points (guarantees zero crashes)
        if not mcq_blocks and not tf_blocks and not short_blocks:
            try:
                key_pts = json.loads(summary_record.key_points)
            except Exception:
                key_pts = [summary_record.key_points]
            key_pts = [pt.strip() for pt in key_pts if pt.strip()]
            if not key_pts:
                key_pts = ["Study document details and summary key points."]
                
            # MCQ Fallbacks
            mcq_blocks = []
            for i, pt in enumerate(key_pts[:3]):
                pt_clean = pt.strip(".-* ")
                mcq_blocks.append(
                    f"Q: What is a key concept discussed in this section?\n"
                    f"A) {pt_clean}\n"
                    f"B) Unrelated external theories\n"
                    f"C) General web technologies\n"
                    f"D) System environment settings\n"
                    f"Correct: A\n"
                    f"Explanation: The document explicitly mentions: {pt_clean}"
                )
            # TF Fallbacks
            tf_blocks = []
            for i, pt in enumerate(key_pts[:3]):
                pt_clean = pt.strip(".-* ")
                tf_blocks.append(
                    f"Q: True or False: {pt_clean}?\n"
                    f"Correct: True\n"
                    f"Explanation: Grounded in document details."
                )
            # Short Answer Fallbacks
            short_blocks = []
            for i, pt in enumerate(key_pts[:3]):
                pt_clean = pt.strip(".-* ")
                words = pt_clean.split()
                keyword = words[0] if words else "Details"
                short_blocks.append(
                    f"Q: Complete this concept: {pt_clean}?\n"
                    f"Correct: {keyword}\n"
                    f"Explanation: Refers to {pt_clean}."
                )

        # Create Quiz Record
        db_quiz = Quiz(document_id=document_id, user_id=user_id)
        db.add(db_quiz)
        db.commit()
        db.refresh(db_quiz)
        
        # Helper to extract fields tolerantly
        def parse_field(pattern, block, default=""):
            m = re.search(pattern, block, re.DOTALL | re.IGNORECASE)
            return m.group(1).strip() if m else default

        # Process MCQs
        for block in mcq_blocks:
            q_text = parse_field(r'(?:Q|Question):\s*(.*?)(?=\s*(?:[A-D][\)\.\:-]|- [A-D][\)\.\:-])|\s*(?:Correct|Answer):|$)', block)
            opt_a = parse_field(r'(?:A[\)\.\:-]|- A[\)\.\:-])\s*(.*?)(?=\s*(?:[B-D][\)\.\:-]|- [B-D][\)\.\:-])|\s*(?:Correct|Answer):|$)', block)
            opt_b = parse_field(r'(?:B[\)\.\:-]|- B[\)\.\:-])\s*(.*?)(?=\s*(?:[C-D][\)\.\:-]|- [C-D][\)\.\:-])|\s*(?:Correct|Answer):|$)', block)
            opt_c = parse_field(r'(?:C[\)\.\:-]|- C[\)\.\:-])\s*(.*?)(?=\s*(?:D[\)\.\:-]|- D[\)\.\:-])|\s*(?:Correct|Answer):|$)', block)
            opt_d = parse_field(r'(?:D[\)\.\:-]|- D[\)\.\:-])\s*(.*?)(?=\s*(?:Correct|Answer):|$)', block)
            correct = parse_field(r'(?:Correct|Answer):\s*(.*?)(?=\s*Explanation:|$)', block).strip().upper()
            explanation = parse_field(r'Explanation:\s*(.*)', block)
            
            # Clean correct answer character defensively
            correct_clean = "A"
            if correct:
                ans_match = re.search(r'\b([A-D])\b', correct)
                if ans_match:
                    correct_clean = ans_match.group(1)
                else:
                    clean_str = "".join([c for c in correct if c in "ABCD"])
                    if clean_str:
                        correct_clean = clean_str[0]
            
            db_q = QuizQuestion(
                quiz_id=db_quiz.id,
                question_type="mcq",
                question_text=q_text or "Question details",
                options=json.dumps([opt_a or "Option A", opt_b or "Option B", opt_c or "Option C", opt_d or "Option D"]),
                correct_answer=correct_clean,
                explanation=explanation or "Verified grounded fact."
            )
            db.add(db_q)

        # Process T/Fs
        for block in tf_blocks:
            q_text = parse_field(r'(?:Q|Question):\s*(.*?)(?=\s*(?:Correct|Answer):|$)', block)
            correct = parse_field(r'(?:Correct|Answer):\s*(.*?)(?=\s*Explanation:|$)', block).strip().capitalize()
            explanation = parse_field(r'Explanation:\s*(.*)', block)
            
            db_q = QuizQuestion(
                quiz_id=db_quiz.id,
                question_type="tf",
                question_text=q_text or "Question details",
                options=json.dumps(["True", "False"]),
                correct_answer=correct or "True",
                explanation=explanation or "Verified grounded fact."
            )
            db.add(db_q)

        # Process Short Answers
        for block in short_blocks:
            q_text = parse_field(r'(?:Q|Question):\s*(.*?)(?=\s*(?:Correct|Answer):|$)', block)
            correct = parse_field(r'(?:Correct|Answer):\s*(.*?)(?=\s*Explanation:|$)', block).strip()
            explanation = parse_field(r'Explanation:\s*(.*)', block)
            
            db_q = QuizQuestion(
                quiz_id=db_quiz.id,
                question_type="short",
                question_text=q_text or "Question details",
                correct_answer=correct or "Yes",
                explanation=explanation or "Verified grounded fact."
            )
            db.add(db_q)
            
        db.commit()
        db.refresh(db_quiz)
        return db_quiz

    async def generate_flashcards(self, document_id: int, user_id: int, db: Session) -> FlashcardSet:
        """
        Generates and persists a set of Q&A flashcards.
        """
        summary_record = db.query(DocumentSummary).filter(DocumentSummary.document_id == document_id).first()
        if not summary_record:
            summary_record = await self.generate_document_summary(document_id, db)
            
        summary_context = summary_record.summary_text
        
        system_prompt = (
            "You are an academic study partner. Design 6 study flashcards based on the document summary.\n"
            "Each flashcard must contain a concise question/term on the front and a concise definition/answer on the back.\n"
            "You MUST respond in this exact format with the [CARD_START] and [CARD_END] tags:\n"
            "[CARD_START]\n"
            "Front: [Question/term here]\n"
            "Back: [Answer/definition here]\n"
            "[CARD_END]"
        )
        
        prompt = f"Document Summary:\n\n{summary_context}"
        response = await llm_service.generate_response(prompt=prompt, system_prompt=system_prompt, temperature=0.7)
        
        card_blocks = re.findall(r'\[CARD_START\](.*?)\[CARD_END\]', response, re.DOTALL | re.IGNORECASE)
        
        if not card_blocks:
            # Fallback parse of lines if LLM output didn't match tags exactly
            card_blocks = []
            lines = response.split('\n')
            current_card = {}
            for line in lines:
                if line.lower().startswith("front:"):
                    current_card["front"] = line[6:].strip()
                elif line.lower().startswith("back:"):
                    current_card["back"] = line[5:].strip()
                    if "front" in current_card:
                        card_blocks.append(f"Front: {current_card['front']}\nBack: {current_card['back']}")
                        current_card = {}
                        
        # Grounded rule-based flashcard generation fallback using summary key points (guarantees zero empty flashcards)
        if not card_blocks:
            try:
                key_pts = json.loads(summary_record.key_points)
            except Exception:
                key_pts = [summary_record.key_points]
            key_pts = [pt.strip() for pt in key_pts if pt.strip()]
            if not key_pts:
                key_pts = ["Study document details and summary key points."]
                
            for pt in key_pts[:6]:
                pt_clean = pt.strip(".-* ")
                card_blocks.append(
                    f"Front: Key Concept in this section\n"
                    f"Back: {pt_clean}"
                )

        db_set = FlashcardSet(document_id=document_id, user_id=user_id)
        db.add(db_set)
        db.commit()
        db.refresh(db_set)
        
        for block in card_blocks:
            front = "Question/term details"
            back = "Answer details"
            
            front_match = re.search(r'Front:\s*(.*?)(?=\s*Back:|$)', block, re.DOTALL | re.IGNORECASE)
            back_match = re.search(r'Back:\s*(.*)', block, re.DOTALL | re.IGNORECASE)
            
            if front_match:
                front = front_match.group(1).strip()
            if back_match:
                back = back_match.group(1).strip()
                
            db_card = Flashcard(
                set_id=db_set.id,
                front=front,
                back=back
            )
            db.add(db_card)
            
        db.commit()
        db.refresh(db_set)
        return db_set

# Global study service singleton
study_service = StudyService()
