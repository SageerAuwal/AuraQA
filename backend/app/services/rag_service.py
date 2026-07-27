from sqlalchemy.orm import Session
from typing import Dict, Any, List, Tuple, Optional
from app.services.embedding_service import embedding_service
from app.services.vectorstore_service import vectorstore_service
from app.services.llm_service import llm_service
from app.models.models import DocumentChunk
from app.api.endpoints.upload import detect_document_language
from app.core.config import settings

class RAGService:
    async def _answer_via_summary(self, document_id: int, query_text: str, max_score: float, db: Session) -> Dict[str, Any]:
        """Helper to check if a query can be answered using the general Document Summary."""
        from app.services.study_service import study_service
        from app.models.models import DocumentSummary
        
        db_summary = db.query(DocumentSummary).filter(DocumentSummary.document_id == document_id).first()
        if not db_summary:
            try:
                db_summary = await study_service.generate_document_summary(document_id, db)
            except Exception:
                db_summary = None
                
        if db_summary:
            import json
            try:
                key_pts = json.loads(db_summary.key_points)
                key_pts_str = "\n".join([f"- {pt}" for pt in key_pts])
            except Exception:
                key_pts_str = db_summary.key_points
                
            summary_context = (
                f"Document Summary: {db_summary.summary_text}\n"
                f"Key Concepts:\n{key_pts_str}\n"
                f"Conclusions: {db_summary.conclusions}"
            )
            detected_lang = detect_document_language(query_text)
            
            system_prompt = (
                "You are a helpful AI assistant. Answer the user's question based on the provided general Document Summary.\n"
                "Keep your answer extremely brief, factual, and direct (at most 2 short sentences). Do not make up facts.\n"
                "If the question cannot be answered using the general Document Summary, you MUST respond with: 'NOT_FOUND'.\n"
                f"IMPORTANT: You MUST write your response in the same language as the user's query (ISO code: {detected_lang})."
            )
            user_prompt = f"Context:\n{summary_context}\n\nQuestion: {query_text}\nAnswer:"
            
            summary_answer = await llm_service.generate_response(prompt=user_prompt, system_prompt=system_prompt)
            
            if "not_found" not in summary_answer.lower():
                return {
                    "answer": summary_answer,
                    "sources": [{"page_number": 1, "score": float(max_score)}],
                    "max_score": float(max_score),
                    "out_of_scope": False
                }
        return None

    def _heuristic_correct_spelling(self, text: str) -> str:
        """
        Applies a spelling corrector for common query words
        to handle typos and spelling mistakes using a pre-defined typo map.
        """
        dictionary = {
            "about": ["abotu", "abou", "abot", "aboutt", "aboot"],
            "document": ["documnt", "documet", "documnet", "docment", "documnts", "documentss"],
            "summary": ["sumary", "summarie", "summaries", "summry", "sumer"],
            "summarize": ["summarise", "sumarize", "sumarise", "summarise", "sumaris", "sumariz"],
            "explain": ["explane", "expln", "explayn", "explian"],
            "what": ["wht", "wahat", "whaat", "wat"],
            "tell": ["tel", "telll"],
            "file": ["fille", "fiel", "files", "filles"],
            "chat": ["cahat", "chaat", "cht", "chats"],
            "concept": ["concpt", "consept"],
            "chapter": ["chaptr", "chapt", "chapetr"]
        }
        
        typo_map = {}
        for correct, typos in dictionary.items():
            for typo in typos:
                typo_map[typo] = correct
                
        words = text.split()
        corrected_words = []
        for w in words:
            # Strip punctuation from word to match
            w_clean = w.lower().strip("?,.!;:()\"'")
            punctuation_before = w[:len(w) - len(w.lstrip("?,.!;:()\"'"))]
            punctuation_after = w[len(w.rstrip("?,.!;:()\"'")):]
            
            if not w_clean:
                corrected_words.append(w)
                continue
                
            # Check direct dictionary map
            if w_clean in typo_map:
                corrected_w = typo_map[w_clean]
            else:
                corrected_w = w_clean
                            
            # Preserve original capitalization if matched/corrected
            if w_clean != corrected_w:
                if w.isupper():
                    corrected_w = corrected_w.upper()
                elif w[0].isupper():
                    corrected_w = corrected_w.capitalize()
                    
            corrected_words.append(punctuation_before + corrected_w + punctuation_after)
            
        return " ".join(corrected_words)

    async def _classify_and_correct_query(self, query_text: str) -> Tuple[str, str]:
        """
        Deterministically classifies the query into categories ('GLOBAL', 'SPECIFIC', or 'GREETING')
        after applying heuristic spelling correction, bypassing the slow, resource-heavy LLM call.
        """
        # Pre-correct spelling mistakes to make matching robust
        pre_corrected = self._heuristic_correct_spelling(query_text)
        
        query_clean = pre_corrected.lower().strip("?.! ")
        
        # Check for simple greetings
        greetings = {"hello", "hi", "hey", "good morning", "good afternoon", "bonjour", "salut", "hola", "hallo", "marhaba", "sannu"}
        if query_clean in greetings or any(query_clean.startswith(g + " ") for g in greetings):
            return pre_corrected, "GREETING"
            
        global_indicators = [
            "summary", "summarize", "summarise", "overview", "about the file", "about the document", 
            "about this", "tell me about", "outline", "synopsis", "takeaway", "key point", "key concept",
            "explain the file", "explain the document", "explain this file", "explain this document",
            "what is this", "what does this file", "what does this document", "what is this report",
            "tell me about it", "what does it say", "what is it", "what is the document about",
            "explain", "concept", "concepts", "chapter", "chapters",
            "résumé", "resumer", "aperçu", "apercu", "à propos", "a propos", "parle-moi", "parler de", "points clés", "points cles",
            "resumen", "resumir", "descripción", "descripcion", "sobre el", "cuéntame", "cuentame", "puntos clave",
            "zusammenfassung", "zusammenfassen", "überblick", "uberblick", "über die", "uber die", "erzähl mir", "erzahl mir", "hauptpunkte",
            "ملخص", "تلخيص", "نظرة عامة", "عن الملف", "عن المستند", "أخبرني", "النقاط الرئيسية",
            "takaice", "bayanin", "game da", "takarda", "taƙaita"
        ]
        is_global = any(kw in query_clean for kw in global_indicators)
        category = "GLOBAL" if is_global else "SPECIFIC"
        return pre_corrected, category

    def _get_out_of_scope_prefix(self, lang: str) -> str:
        prefixes = {
            "en": "This query is out of the scope of the document context, but here is the answer:\n\n",
            "fr": "Cette requête est hors de portée du contexte du document, mais voici la réponse :\n\n",
            "es": "Esta consulta está fuera del alcance del contexto del documento, pero aquí está la respuesta:\n\n",
            "de": "Diese Anfrage liegt außerhalb des Rahmens des Dokumentenkontexts, aber hier ist die Antwort:\n\n",
            "ar": "هذا الاستعلام خارج نطاق سياق المستند، ولكن إليك الإجابة:\n\n",
            "ha": "Wannan tambaya tana waje da mahallin takardar, amma ga amsar:\n\n"
        }
        return prefixes.get(lang.lower(), prefixes["en"])

    async def answer_question(self, document_id: Optional[int], query_text: str, db: Session, chat_id: int = None, all_documents: bool = False) -> Dict[str, Any]:
        """
        Main retrieval-augmented generation pipeline.
        0. Clean and classify the query (handles typos and spelling errors).
        1. Resolve target document IDs (isolated in-chat, single document, or library).
        2. If no target documents, answer using general knowledge.
        3. If target documents, search FAISS and filter by target documents.
        4. If match is above threshold, generate response grounded in context.
        5. If match is below threshold, generate general response with out-of-scope disclaimer.
        """
        from app.models.models import Chat, Document
        
        # Resolve user_id from chat session
        user_id = None
        if chat_id is not None:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                user_id = chat.user_id

        # Determine target doc IDs to scope the search
        doc_ids = []
        if document_id is not None:
            doc_ids = [document_id]
        elif all_documents and user_id is not None:
            user_docs = db.query(Document).filter(Document.user_id == user_id, Document.chat_id == None).all()
            doc_ids = [doc.id for doc in user_docs]
        elif chat_id is not None:
            chat_docs = db.query(Document).filter(Document.chat_id == chat_id).all()
            doc_ids = [doc.id for doc in chat_docs]

        # Step 0: Clean query and classify intent (corrects spelling mistakes dynamically)
        corrected_query, category = await self._classify_and_correct_query(query_text)
        detected_lang = detect_document_language(corrected_query)

        # Retrieve short-term memory (conversation history) if chat_id is specified
        history_context = ""
        if chat_id is not None:
            from app.models.models import Message
            # The current user message is already added and committed in database, so limit to 6 (5 history + 1 current)
            history_msgs = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.timestamp.desc()).limit(6).all()
            history_msgs.reverse()
            if len(history_msgs) > 1:
                history_list = []
                for msg in history_msgs[:-1]: # exclude current message
                    role_str = "User" if msg.role == "user" else "Assistant"
                    history_list.append(f"{role_str}: {msg.content}")
                history_context = "\n".join(history_list)

        # Handle simple greetings first
        if category == "GREETING":
            greetings_map = {
                "en": "Hello! How can I help you today?",
                "fr": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
                "es": "¡Hola! ¿Cómo puedo ayudarte hoy?",
                "de": "Hallo! Wie kann ich Ihnen heute helfen?",
                "ar": "مرحباً! كيف يمكنني مساعدتك اليوم؟",
                "ha": "Sannu! Yaya zan iya taimaka muku yau?"
            }
            if doc_ids:
                greetings_map = {
                    "en": "Hello! How can I help you today with these documents?",
                    "fr": "Bonjour ! Comment puis-je vous aider aujourd'hui avec ces documents ?",
                    "es": "¡Hola! ¿Cómo puedo ayudarte hoy con estos documentos?",
                    "de": "Hallo! Wie kann ich Ihnen heute mit diesen Dokumenten helfen?",
                    "ar": "مرحباً! كيف يمكنني مساعدتك اليوم في هذه المستندات؟",
                    "ha": "Sannu! Yaya zan iya taimaka muku yau da wadannan takardu?"
                }
            answer = greetings_map.get(detected_lang, greetings_map["en"])
            return {
                "answer": answer,
                "sources": [],
                "max_score": 0.0,
                "out_of_scope": False
            }

        # Case A: Pure General AI Mode (no target documents)
        if not doc_ids:
            system_prompt = (
                "You are AuraQA, a helpful, intelligent, and secure offline AI assistant.\n"
                "Provide detailed, smart, and context-aware responses to the user's questions.\n"
                "Use the 'Recent Chat History' to understand the context of the conversation and resolve references to previous turns.\n"
                f"IMPORTANT: You MUST write your response in the same language as the user's query (ISO code: {detected_lang})."
            )
            user_prompt = ""
            if history_context:
                user_prompt += f"Recent Chat History:\n{history_context}\n\n"
            user_prompt += f"Question: {corrected_query}\nAnswer:"
            
            answer = await llm_service.generate_response(prompt=user_prompt, system_prompt=system_prompt, temperature=0.7)
            return {
                "answer": answer,
                "sources": [],
                "max_score": 0.0,
                "out_of_scope": False
            }

        # Case B: Grounded RAG Mode
        # If the query is global/conceptual, try summary first (only if single doc)
        if category == "GLOBAL" and len(doc_ids) == 1:
            summary_res = await self._answer_via_summary(doc_ids[0], corrected_query, 1.0, db)
            if summary_res:
                return summary_res

        # Retrieve relevant chunks from FAISS
        query_emb = embedding_service.get_embedding(corrected_query)
        faiss_results = vectorstore_service.search(query_emb, k=50)
        
        db_chunks = []
        matched_scores = {}
        if faiss_results:
            matched_scores = {chunk_id: score for chunk_id, score in faiss_results}
            matched_ids = list(matched_scores.keys())
            db_chunks = db.query(DocumentChunk).filter(
                DocumentChunk.id.in_(matched_ids),
                DocumentChunk.document_id.in_(doc_ids)
            ).all()

        is_grounded_match = False
        max_score = 0.0
        top_chunks = []
        if db_chunks:
            chunks_with_scores = []
            for chunk in db_chunks:
                score = matched_scores.get(chunk.id, 0.0)
                chunks_with_scores.append((chunk, score))
            chunks_with_scores.sort(key=lambda x: x[1], reverse=True)
            top_chunks = chunks_with_scores[:2]
            max_score = top_chunks[0][1]
            if max_score >= settings.SIMILARITY_THRESHOLD:
                is_grounded_match = True

        if is_grounded_match:
            # Map doc IDs to filenames for dynamic prefixing
            doc_id_to_filename = {}
            docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
            for doc in docs:
                doc_id_to_filename[doc.id] = doc.filename
                
            context_blocks = []
            sources = []
            for chunk, score in top_chunks:
                filename = doc_id_to_filename.get(chunk.document_id, "Document")
                context_blocks.append(f"[Source File: {filename}, Page/Row {chunk.page_number}]: {chunk.text}")
                sources.append({
                    "page_number": chunk.page_number,
                    "score": float(f"{score:.4f}"),
                    "title": filename
                })
            context = "\n\n".join(context_blocks)
            
            system_prompt = (
                "You are a helpful AI assistant. Answer the user's question based strictly and ONLY on the provided Context.\n"
                "Keep your answer extremely brief, factual, and direct (at most 2 short sentences). Do not make up facts, extrapolate, or mention external info.\n"
                "If the answer is not contained in the Context, respond with: 'This answer is not available in the uploaded document.'\n"
                "Use the 'Recent Chat History' to understand the context of the conversation and resolve references (like 'it', 'they', 'the first one', 'what you said earlier') to previous turns.\n"
                f"IMPORTANT: You MUST write your response in the same language as the user's query (ISO code: {detected_lang})."
            )
            
            user_prompt = f"Context:\n{context}\n\n"
            if history_context:
                user_prompt += f"Recent Chat History:\n{history_context}\n\n"
            user_prompt += f"Question: {corrected_query}\nAnswer:"
            
            answer = await llm_service.generate_response(prompt=user_prompt, system_prompt=system_prompt, temperature=0.0)
            
            if "not available in the uploaded document" not in answer.lower():
                return {
                    "answer": answer,
                    "sources": sources,
                    "max_score": float(f"{max_score:.4f}"),
                    "out_of_scope": False
                }

        # Fallback to Summary (if single document) or General Knowledge with Disclaimer (out of scope)
        if len(doc_ids) == 1:
            summary_res = await self._answer_via_summary(doc_ids[0], corrected_query, max_score, db)
            if summary_res:
                return summary_res

        # Call LLM using general knowledge system prompt
        system_prompt = (
            "You are a helpful AI assistant. Answer the user's question using your general knowledge.\n"
            "Keep your answer brief, factual, and direct.\n"
            "Use the 'Recent Chat History' to understand the context of the conversation and resolve references to previous turns.\n"
            "Do NOT mention that you are answering using general knowledge or that the context is missing, as a warning prefix has already been added to your response.\n"
            f"IMPORTANT: You MUST write your response in the same language as the user's query (ISO code: {detected_lang})."
        )
        user_prompt = ""
        if history_context:
            user_prompt += f"Recent Chat History:\n{history_context}\n\n"
        user_prompt += f"Question: {corrected_query}\nAnswer:"
        
        answer = await llm_service.generate_response(prompt=user_prompt, system_prompt=system_prompt, temperature=0.7)
        
        prefix = self._get_out_of_scope_prefix(detected_lang)
        final_answer = prefix + answer
        
        return {
            "answer": final_answer,
            "sources": [],
            "max_score": float(f"{max_score:.4f}"),
            "out_of_scope": True
        }

    async def answer_question_stream(self, document_id: Optional[int], query_text: str, db: Session, chat_id: int = None, all_documents: bool = False):
        """
        Asynchronously streams the RAG QA pipeline response.
        Yields text token string chunks.
        """
        from app.models.models import Chat, Document
        
        # Resolve user_id from chat session
        user_id = None
        if chat_id is not None:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                user_id = chat.user_id

        # Determine target doc IDs to scope the search
        doc_ids = []
        if document_id is not None:
            doc_ids = [document_id]
        elif all_documents and user_id is not None:
            user_docs = db.query(Document).filter(Document.user_id == user_id, Document.chat_id == None).all()
            doc_ids = [doc.id for doc in user_docs]
        elif chat_id is not None:
            chat_docs = db.query(Document).filter(Document.chat_id == chat_id).all()
            doc_ids = [doc.id for doc in chat_docs]

        # Step 0: Clean query and classify intent (corrects spelling mistakes dynamically)
        corrected_query, category = await self._classify_and_correct_query(query_text)
        detected_lang = detect_document_language(corrected_query)

        # Retrieve short-term memory (conversation history) if chat_id is specified
        history_context = ""
        if chat_id is not None:
            from app.models.models import Message
            # The current user message is already added and committed in database, so limit to 6 (5 history + 1 current)
            history_msgs = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.timestamp.desc()).limit(6).all()
            history_msgs.reverse()
            if len(history_msgs) > 1:
                history_list = []
                for msg in history_msgs[:-1]: # exclude current message
                    role_str = "User" if msg.role == "user" else "Assistant"
                    history_list.append(f"{role_str}: {msg.content}")
                history_context = "\n".join(history_list)

        # Handle simple greetings first
        if category == "GREETING":
            greetings_map = {
                "en": "Hello! How can I help you today?",
                "fr": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
                "es": "¡Hola! ¿Cómo puedo ayudarte hoy?",
                "de": "Hallo! Wie kann ich Ihnen heute helfen?",
                "ar": "مرحباً! كيف يمكنني مساعدتك اليوم؟",
                "ha": "Sannu! Yaya zan iya taimaka muku yau?"
            }
            if doc_ids:
                greetings_map = {
                    "en": "Hello! How can I help you today with these documents?",
                    "fr": "Bonjour ! Comment puis-je vous aider aujourd'hui avec ces documents ?",
                    "es": "¡Hola! ¿Cómo puedo ayudarte hoy con estos documentos?",
                    "de": "Hallo! Wie kann ich Ihnen heute mit diesen Dokumenten helfen?",
                    "ar": "مرحباً! كيف يمكنني مساعدتك اليوم في هذه المستندات؟",
                    "ha": "Sannu! Yaya zan iya taimaka muku yau da wadannan takardu?"
                }
            answer = greetings_map.get(detected_lang, greetings_map["en"])
            import asyncio
            for word in answer.split(" "):
                yield word + " "
                await asyncio.sleep(0.015)
            return

        # Case A: Pure General AI Mode (no target documents)
        if not doc_ids:
            system_prompt = (
                "You are AuraQA, a helpful, intelligent, and secure offline AI assistant.\n"
                "Provide detailed, smart, and context-aware responses to the user's questions.\n"
                "Use the 'Recent Chat History' to understand the context of the conversation and resolve references to previous turns.\n"
                f"IMPORTANT: You MUST write your response in the same language as the user's query (ISO code: {detected_lang})."
            )
            user_prompt = ""
            if history_context:
                user_prompt += f"Recent Chat History:\n{history_context}\n\n"
            user_prompt += f"Question: {corrected_query}\nAnswer:"
            
            async for token in llm_service.stream_response(prompt=user_prompt, system_prompt=system_prompt, temperature=0.7):
                yield token
            return

        # Case B: Grounded RAG Mode
        # If the query is global/conceptual, try summary first (only if single doc)
        if category == "GLOBAL" and len(doc_ids) == 1:
            summary_res = await self._answer_via_summary(doc_ids[0], corrected_query, 1.0, db)
            if summary_res:
                import asyncio
                for word in summary_res["answer"].split(" "):
                    yield word + " "
                    await asyncio.sleep(0.015)
                return

        # Retrieve relevant chunks from FAISS
        query_emb = embedding_service.get_embedding(corrected_query)
        faiss_results = vectorstore_service.search(query_emb, k=50)
        
        db_chunks = []
        matched_scores = {}
        if faiss_results:
            matched_scores = {chunk_id: score for chunk_id, score in faiss_results}
            matched_ids = list(matched_scores.keys())
            db_chunks = db.query(DocumentChunk).filter(
                DocumentChunk.id.in_(matched_ids),
                DocumentChunk.document_id.in_(doc_ids)
            ).all()

        is_grounded_match = False
        max_score = 0.0
        top_chunks = []
        if db_chunks:
            chunks_with_scores = []
            for chunk in db_chunks:
                score = matched_scores.get(chunk.id, 0.0)
                chunks_with_scores.append((chunk, score))
            chunks_with_scores.sort(key=lambda x: x[1], reverse=True)
            top_chunks = chunks_with_scores[:2]
            max_score = top_chunks[0][1]
            if max_score >= settings.SIMILARITY_THRESHOLD:
                is_grounded_match = True

        if is_grounded_match:
            doc_id_to_filename = {}
            docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
            for doc in docs:
                doc_id_to_filename[doc.id] = doc.filename
                
            context_blocks = []
            for chunk, score in top_chunks:
                filename = doc_id_to_filename.get(chunk.document_id, "Document")
                context_blocks.append(f"[Source File: {filename}, Page/Row {chunk.page_number}]: {chunk.text}")
            context = "\n\n".join(context_blocks)
            
            system_prompt = (
                "You are a helpful AI assistant. Answer the user's question based strictly and ONLY on the provided Context.\n"
                "Keep your answer extremely brief, factual, and direct (at most 2 short sentences). Do not make up facts, extrapolate, or mention external info.\n"
                "If the answer is not contained in the Context, respond with: 'This answer is not available in the uploaded document.'\n"
                "Use the 'Recent Chat History' to understand the context of the conversation and resolve references (like 'it', 'they', 'the first one', 'what you said earlier') to previous turns.\n"
                f"IMPORTANT: You MUST write your response in the same language as the user's query (ISO code: {detected_lang})."
            )
            
            user_prompt = f"Context:\n{context}\n\n"
            if history_context:
                user_prompt += f"Recent Chat History:\n{history_context}\n\n"
            user_prompt += f"Question: {corrected_query}\nAnswer:"
            
            collected_tokens = []
            async for token in llm_service.stream_response(prompt=user_prompt, system_prompt=system_prompt, temperature=0.0):
                collected_tokens.append(token)
            
            full_answer = "".join(collected_tokens)
            if "not available in the uploaded document" not in full_answer.lower():
                for token in collected_tokens:
                    yield token
                return

        # Fallback to Summary (if single document) or General Knowledge with Disclaimer (out of scope)
        if len(doc_ids) == 1:
            summary_res = await self._answer_via_summary(doc_ids[0], corrected_query, max_score, db)
            if summary_res:
                import asyncio
                for word in summary_res["answer"].split(" "):
                    yield word + " "
                    await asyncio.sleep(0.015)
                return

        # Prepend out of scope prefix first
        prefix = self._get_out_of_scope_prefix(detected_lang)
        yield prefix
            
        system_prompt = (
            "You are a helpful AI assistant. Answer the user's question using your general knowledge.\n"
            "Keep your answer brief, factual, and direct.\n"
            "Use the 'Recent Chat History' to understand the context of the conversation and resolve references to previous turns.\n"
            "Do NOT mention that you are answering using general knowledge or that the context is missing, as a warning prefix has already been added to your response.\n"
            f"IMPORTANT: You MUST write your response in the same language as the user's query (ISO code: {detected_lang})."
        )
        user_prompt = ""
        if history_context:
            user_prompt += f"Recent Chat History:\n{history_context}\n\n"
        user_prompt += f"Question: {corrected_query}\nAnswer:"
        
        async for token in llm_service.stream_response(prompt=user_prompt, system_prompt=system_prompt, temperature=0.7):
            yield token

# Global RAG service singleton
rag_service = RAGService()
